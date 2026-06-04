#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sheets-direct.py  v1.0
快速 Sheets 直連工具（混合架構 — 讀取 + 小寫入）

用途：
  - 快速讀取任意分頁/範圍（不需跑完整 sync 流程）
  - 單格/小範圍寫入（不覆蓋整個分頁）
  - 輕量查詢（看日報、查單一影片狀態）

設計原則：
  - 複用 lib/sheets_auth.py + lib/sheets_api.py（零重複程式碼）
  - 批量同步仍走 sync-to-sheets.py（有 git 審計 + 完整格式化）
  - 本工具只做「點查」和「點寫」

使用方式：
  python sheets-direct.py read SHEET [RANGE]        → 讀取分頁（預設 A1:Z100）
  python sheets-direct.py read-cell SHEET CELL       → 讀取單格
  python sheets-direct.py write-cell SHEET CELL VAL  → 寫入單格
  python sheets-direct.py tabs                       → 列出所有分頁名稱
  python sheets-direct.py employee [YYYY-MM-DD]      → 快速看日報
  python sheets-direct.py lookup-vid VID-NNN         → 查影片在 Sheets 上的狀態
"""

import sys

from lib.config import DEFAULT_OPERATOR, SH_EMPLOYEE_LOG, SH_VIDEO_OVERVIEW, OPERATOR_SHEETS
from lib.sheets_auth import load_credentials, get_access_token
from lib.sheets_api import (
    sheets_read, sheets_write, sheets_get_tab_names,
)


def _auth():
    """認證並回傳 access token。"""
    creds = load_credentials()
    return get_access_token(creds)


def cmd_read(args):
    """讀取指定分頁的資料。"""
    if not args:
        print("用法：sheets-direct.py read SHEET [RANGE]")
        print("範例：sheets-direct.py read 影片總覽")
        print("範例：sheets-direct.py read 待辦 A1:D20")
        sys.exit(1)

    sheet = args[0]
    range_str = args[1] if len(args) > 1 else "A1:Z100"

    token = _auth()
    rows = sheets_read(token, sheet, range_str)

    if not rows:
        print(f"（「{sheet}」{range_str} 無資料）")
        return

    # 計算每欄最大寬度（上限 40 字元）
    col_widths = []
    for row in rows:
        for i, cell in enumerate(row):
            w = min(len(str(cell or "")), 40)
            if i >= len(col_widths):
                col_widths.append(w)
            else:
                col_widths[i] = max(col_widths[i], w)

    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            val = str(cell or "")
            width = col_widths[i] if i < len(col_widths) else 10
            cells.append(val.ljust(width)[:width])
        print(" | ".join(cells).rstrip())


def cmd_read_cell(args):
    """讀取單一儲存格。"""
    if len(args) < 2:
        print("用法：sheets-direct.py read-cell SHEET CELL")
        print("範例：sheets-direct.py read-cell 影片總覽 A2")
        sys.exit(1)

    sheet, cell = args[0], args[1]
    token = _auth()
    rows = sheets_read(token, sheet, f"{cell}:{cell}")

    if rows and rows[0]:
        print(rows[0][0])
    else:
        print(f"（{sheet}!{cell} 為空）")


def cmd_write_cell(args):
    """寫入單一儲存格或小範圍。"""
    if len(args) < 3:
        print("用法：sheets-direct.py write-cell SHEET CELL VALUE")
        print("範例：sheets-direct.py write-cell 影片總覽 H3 '✅ 完整'")
        sys.exit(1)

    sheet, cell, value = args[0], args[1], args[2]
    token = _auth()
    sheets_write(token, sheet, cell, [[value]])
    print(f"✅ 已寫入 {sheet}!{cell} = {value}")


def cmd_tabs(_args):
    """列出所有分頁名稱。"""
    token = _auth()
    tabs = sheets_get_tab_names(token)
    print(f"旺來總表共 {len(tabs)} 個分頁：")
    for i, t in enumerate(tabs, 1):
        print(f"  {i}. {t}")


def cmd_employee(args):
    """快速讀取日報資料（可選日期過濾）。"""
    token = _auth()
    rows = sheets_read(token, SH_EMPLOYEE_LOG, "A1:F500")

    if not rows:
        print("（日報目前無資料）")
        return

    filter_date = args[0] if args else None

    # 跳過看板行（前 6 行），只顯示資料
    data_start = 6  # LOG_DATA_START_ROW - 1 (0-indexed)
    header_printed = False

    for i, row in enumerate(rows):
        if i < data_start:
            continue
        if not any((cell or "").strip() for cell in row):
            continue

        date_val = (row[0] or "").lstrip("'").strip() if row else ""

        if filter_date and date_val != filter_date:
            continue

        if not header_printed:
            print("日期       | 姓名 | 類別 | 做了什麼 | 花多久 | 備註")
            print("-" * 60)
            header_printed = True

        line = " | ".join((cell or "").strip() for cell in row[:6])
        print(line)

    if not header_printed:
        if filter_date:
            print(f"（{filter_date} 無日報記錄）")
        else:
            print("（日報目前無資料）")


def cmd_lookup_vid(args, operator=DEFAULT_OPERATOR):
    """從 Sheets 影片總覽分頁查詢單一影片狀態。"""
    if not args:
        print("用法：sheets-direct.py lookup-vid VID-NNN")
        sys.exit(1)

    target_vid = args[0].upper()
    tab = OPERATOR_SHEETS.get(operator, {}).get("video_overview", SH_VIDEO_OVERVIEW)
    token = _auth()
    rows = sheets_read(token, tab, "A1:H100")

    if not rows or len(rows) < 2:
        print("（影片總覽無資料）")
        return

    header = rows[1] if len(rows) > 1 else []

    for row in rows[2:]:
        if not row:
            continue
        vid = (row[0] or "").strip()
        if vid.upper() == target_vid:
            print(f"📋 {target_vid} Sheets 狀態：")
            for j, cell in enumerate(row):
                label = header[j] if j < len(header) else f"欄{j+1}"
                print(f"  {label}: {cell or '—'}")
            return

    print(f"（Sheets 上找不到 {target_vid}）")


def _pop_operator_arg(args):
    operator = DEFAULT_OPERATOR
    remaining = []
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--operator":
            if idx + 1 >= len(args):
                print("用法：sheets-direct.py --operator OPERATOR COMMAND ...")
                sys.exit(1)
            operator = args[idx + 1].strip().lower()
            idx += 2
            continue
        if arg.startswith("--operator="):
            operator = arg.split("=", 1)[1].strip().lower()
            idx += 1
            continue
        remaining.append(arg)
        idx += 1
    return operator, remaining


def main():
    # 強制 UTF-8 輸出：Windows / 非 UTF-8 locale 下，emoji 輸出被 pipe / 重導 / 捕捉時
    # 預設 locale codec（如 cp950）無法編碼 emoji → print 崩潰。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    if len(sys.argv) < 2:
        print("sheets-direct.py v1.0 — 快速 Sheets 直連工具")
        print()
        print("用法：")
        print("  read SHEET [RANGE]        讀取分頁（預設 A1:Z100）")
        print("  read-cell SHEET CELL      讀取單格")
        print("  write-cell SHEET CELL VAL 寫入單格")
        print("  tabs                      列出所有分頁")
        print("  employee [YYYY-MM-DD]     快速看日報")
        print("  lookup-vid VID-NNN        查影片 Sheets 狀態")
        print("  --operator OPERATOR       指定 operator（預設 DEFAULT_OPERATOR）")
        sys.exit(0)

    operator, argv = _pop_operator_arg(sys.argv[1:])
    if not argv:
        print("❌ 缺少指令")
        sys.exit(1)
    cmd = argv[0].lower().replace("_", "-")
    args = argv[1:]

    commands = {
        "read": cmd_read,
        "read-cell": cmd_read_cell,
        "write-cell": cmd_write_cell,
        "tabs": cmd_tabs,
        "employee": cmd_employee,
        "lookup-vid": cmd_lookup_vid,
    }

    if cmd not in commands:
        print(f"❌ 未知指令：{cmd}")
        print(f"💡 可用指令：{', '.join(sorted(commands))}")
        sys.exit(1)

    try:
        if cmd == "lookup-vid":
            commands[cmd](args, operator=operator)
        else:
            commands[cmd](args)
    except FileNotFoundError:
        from lib.config import CREDENTIALS_PATH
        print(f"❌ 找不到金鑰：{CREDENTIALS_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 執行失敗：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
