#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-to-sheets.py  v5.0
旺來總表 多分頁同步腳本

分頁架構（5 個分頁）：
  靈感庫      — 智能看板：漏斗統計+健康警示+停留天數+緊急旗標，G欄備註手動保留
  影片總覽    — 所有影片狀態+表現+下一步（合併影片追蹤+數據回填）
  待辦        — 智能看板：逾期計數+緊急旗標自動計算+逾期優先排序，E欄備註手動保留
  報表        — 影片產量（週/月）+ 靈感轉化 + 待辦完成統計
  日報        — Crew手動填寫（行1-4=智能看板，行5=分隔線，行6=欄位標頭，行7+=資料）

使用方式：
  python sync-to-sheets.py               → 同步靈感庫 + 待辦
  python sync-to-sheets.py all           → 全部分頁
  python sync-to-sheets.py video         → 影片總覽
  python sync-to-sheets.py todo          → 待辦
  python sync-to-sheets.py report        → 報表（週報+月報+完成統計）
  python sync-to-sheets.py inspiration   → 靈感庫
  python sync-to-sheets.py backfill      → 數據回填
  python sync-to-sheets.py write_backfill  → 數據回填（write_backfill 為 backfill 別名）
  python sync-to-sheets.py tabs          → 列出所有分頁名稱
  python sync-to-sheets.py employee                         → 初始化日報分頁（首次建立用）
  python sync-to-sheets.py log 姓名 類別 做了什麼 花多久 [備註]  → 新增一筆日報
  python sync-to-sheets.py fetch_employee [YYYY-MM-DD]      → 讀取日報（可選日期過濾）
  python sync-to-sheets.py analyze_employee [YYYY-MM-DD]    → 即時智能分析
  python sync-to-sheets.py archive_employee                 → 整理日報：輸出週報 + 刪除資料行
"""

import sys
import json
import urllib.error

from lib.config import SPREADSHEET_ID, SH_EMPLOYEE_LOG, resolve_operator, get_operator_tabs, DEFAULT_OPERATOR
from lib.sheets_auth import load_credentials, get_access_token
from lib.sheets_api import sheets_get_tab_names, sheets_read, _RETRYABLE_CODES
from lib.cloud_relay import _is_cloud_environment, trigger_github_sync
from lib.sync_tabs import (
    sync_inspiration, sync_video_overview, sync_todo,
    sync_report,
    clear_sync_cache,
)
from lib.employee import (
    init_employee_log, append_employee_log,
    analyze_employee_data, archive_employee,
)



def _extract_operator(argv):
    """從 argv 中提取 --operator 參數。回傳 (operator, cleaned_argv)。"""
    cleaned = []
    operator = None
    i = 0
    while i < len(argv):
        if argv[i] == "--operator" and i + 1 < len(argv):
            operator = resolve_operator(argv[i + 1])
            i += 2
        else:
            cleaned.append(argv[i])
            i += 1
    return operator, cleaned


def main():
    operator, cleaned_argv = _extract_operator(sys.argv)
    sys.argv = cleaned_argv
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "default"

    print("=" * 50)
    print("旺來總表 同步腳本 v5.1")
    print("=" * 50)
    if operator:
        print(f"👤 操作員：{operator}")

    # ── 雲端環境偵測 ──
    if _is_cloud_environment():
        print("\n☁️  偵測到雲端環境（Google API 不可達）")
        print("   自動切換 → GitHub Actions 中繼模式")

        direct_only_modes = ("log", "fetch_employee", "analyze_employee", "archive_employee", "employee")
        if mode in direct_only_modes:
            print(f"\n  ❌ 「{mode}」需要直連 Google API，雲端環境不支援")
            print("  💡 請在本地機器執行此指令")
            return

        success = trigger_github_sync(mode)
        if success:
            print(f"\n👉 https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print("\n" + "=" * 50)
        return

    # ── 直連模式 ──
    print("\n[1/3] 載入金鑰...")
    try:
        creds = load_credentials()
        print(f"  服務帳號：{creds['client_email']}")
    except FileNotFoundError:
        from lib.config import CREDENTIALS_PATH
        print(f"  ❌ 找不到金鑰：{CREDENTIALS_PATH}")
        sys.exit(1)
    except json.JSONDecodeError:
        from lib.config import CREDENTIALS_PATH
        print(f"  ❌ 金鑰檔案 JSON 格式錯誤：{CREDENTIALS_PATH}")
        sys.exit(1)
    except KeyError:
        from lib.config import CREDENTIALS_PATH
        print(f"  ❌ 金鑰檔案缺少必要欄位（client_email）：{CREDENTIALS_PATH}")
        sys.exit(1)

    print("\n[2/3] Google 認證...")
    try:
        token = get_access_token(creds)
        print("  ✅ 認證成功")
    except Exception as e:
        print(f"  ❌ 認證失敗：{e}")
        sys.exit(1)

    VALID_MODES = {
        "default", "all", "inspiration", "todo", "video",
        "report", "backfill", "write_backfill", "tabs",
        "employee", "log", "fetch_employee", "analyze_employee",
        "archive_employee",
    }
    if mode not in VALID_MODES:
        print(f"  ❌ 未知的同步模式：「{mode}」")
        print(f"  💡 可用模式：{', '.join(sorted(VALID_MODES))}")
        sys.exit(1)

    print(f"\n[3/3] 同步模式：{mode}")
    sync_results = {}

    def _track_sync(label, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
            sync_results[label] = "✅"
        except Exception as e:
            sync_results[label] = f"❌ {e}"
            if isinstance(e, urllib.error.HTTPError) and e.code not in _RETRYABLE_CODES:
                raise

    try:
        # 決定要同步哪些操作員
        if operator:
            ops_to_sync = [operator]
        else:
            ops_to_sync = [DEFAULT_OPERATOR]

        for op in ops_to_sync:
            op_tabs = get_operator_tabs(op)
            op_label = f"（{op}）" if len(ops_to_sync) > 1 else ""

            if mode in ("default", "all", "inspiration"):
                _track_sync(f"{op_tabs['inspiration']}", sync_inspiration, token, operator=op)

            if mode in ("video", "backfill", "write_backfill", "all"):
                _track_sync(f"{op_tabs['video_overview']}", sync_video_overview, token, operator=op)

            if mode in ("report", "all"):
                from lib.config import SH_REPORT
                _track_sync(f"{SH_REPORT}{op_label}", sync_report, token, operator=op)

        if mode in ("default", "all", "todo"):
            from lib.config import SH_TODO
            _track_sync(SH_TODO, sync_todo, token, operator=resolve_operator(operator))

        if mode == "all":
            _track_sync(SH_EMPLOYEE_LOG, analyze_employee_data, token)

        if mode == "tabs":
            tabs = sheets_get_tab_names(token)
            print(f"  旺來總表共 {len(tabs)} 個分頁：")
            for i, t in enumerate(tabs, 1):
                print(f"    {i}. {t}")

        if mode == "employee":
            init_employee_log(token)

        if mode == "log":
            if len(sys.argv) < 4:
                print("  ❌ 用法：python sync-to-sheets.py log 姓名 完成 [進行中]")
                print("  範例：python sync-to-sheets.py log Wei 剪完2支 粗剪1支")
                return
            append_employee_log(
                token,
                name        = sys.argv[2],
                completed   = sys.argv[3],
                in_progress = sys.argv[4] if len(sys.argv) > 4 else "",
            )

        if mode == "fetch_employee":
            rows = sheets_read(token, SH_EMPLOYEE_LOG, "A1:F500")
            if not rows:
                print("  （日報目前無資料）")
            else:
                filter_date = sys.argv[2] if len(sys.argv) > 2 else None
                for row in rows:
                    if not any((cell or "").strip() for cell in row):
                        continue
                    line = " | ".join((cell or "") for cell in row)
                    if filter_date:
                        if row and row[0].lstrip("'") == filter_date:
                            print(line)
                    else:
                        print(line)

        if mode == "analyze_employee":
            target_date = sys.argv[2] if len(sys.argv) > 2 else None
            analyze_employee_data(token, target_date)

        if mode == "archive_employee":
            archive_employee(token)

    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("  ⚠️ 直連 Sheets API 被擋（HTTP 403），自動切換 GitHub Actions 中繼...")
            relay_modes = {"default", "all", "inspiration", "todo", "video",
                           "report", "backfill"}
            if mode in relay_modes:
                success = trigger_github_sync(mode)
                if success:
                    print(f"\n👉 https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
                else:
                    print("  ❌ GitHub Actions 中繼也失敗，請檢查 GitHub token 或 workflow 設定")
                    sys.exit(1)
            else:
                print(f"  ❌ 「{mode}」不支援中繼，需直連 Google API")
                sys.exit(1)
        else:
            import traceback
            print(f"  ❌ 同步失敗：{e}")
            traceback.print_exc()
            sys.exit(1)
    except Exception as e:
        import traceback
        print(f"  ❌ 同步失敗：{e}")
        traceback.print_exc()
        sys.exit(1)
    else:
        print("\n" + "=" * 50)
        if sync_results:
            failed = [k for k, v in sync_results.items() if v.startswith("❌")]
            for label, result in sync_results.items():
                print(f"  {result} {label}")
            if failed:
                print(f"\n⚠️ 同步部分失敗（{len(failed)}/{len(sync_results)}）")
            else:
                print(f"\n✅ 同步完成！（{len(sync_results)} 個分頁）")
        else:
            print("✅ 同步完成！")
        print(f"👉 https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print("=" * 50)
    finally:
        clear_sync_cache()

if __name__ == "__main__":
    main()
