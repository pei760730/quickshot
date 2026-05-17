#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各分頁同步函數：靈感庫 / 影片總覽 / 待辦 / 報表。
"""

import json
import os
from datetime import timedelta

from .config import (
    PROJECT_ROOT, SH_TODO,
    SH_REPORT,
    resolve_operator,
    get_operator_tabs,
)
from .sheets_api import (
    sheets_clear, sheets_write, sheets_read,
    sheets_get_tab_names, sheets_add_tab, sheets_format_bg,
    sheets_get_last_row,
)
from .scanners import now_tw, scan_inspiration, scan_todos
from scripts.ops.lib.pipeline import get_pipeline_data

from .builders import (
    build_inspiration_rows, build_video_overview_rows,
    build_todo_rows, build_report_rows,
)

# ── 檔案讀取快取（sync all 時共享，避免重複讀同一份 JSON）──
_file_cache = {}


def _load_json_cached(path):
    """讀取 JSON 檔案，同一個 sync session 內快取結果。"""
    path = str(path)
    if path in _file_cache:
        return _file_cache[path]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _file_cache[path] = data
    return data


def clear_sync_cache():
    """清除檔案快取（每次 sync session 結束後呼叫）。"""
    _file_cache.clear()


def _compute_clear_range(new_rows_count, actual_last_row, old_row_count=0):
    """Pure function：計算寫入 new_rows_count 行後，要 clear 的 row 區間。

    設計：
    - clear_start = new_rows_count + 1（第一個要清的 row）
    - fallback_end = max(old_row_count + 5, clear_start + 10)（無 API 時的保底）
    - clear_end = max(actual_last_row + 10, fallback_end)
      → 確保清到 Sheets 實際 last row + 10 緩衝（涵蓋歷史殘留）

    回傳 (clear_start, clear_end)；若 clear_start > clear_end 表示不需清。
    """
    clear_start = new_rows_count + 1
    fallback_end = max(old_row_count + 5, clear_start + 10)
    clear_end = max(actual_last_row + 10, fallback_end)
    return clear_start, clear_end


def _write_then_clear(token, tab_name, range_prefix, max_col, rows, old_row_count=0):
    """Write-first 策略：先寫入資料，再清除殘留行。

    比 clear-then-write 安全：即使 clear 失敗，資料已在 Sheets 上。

    v2（2026-04-19）：透過 `sheets_get_last_row()` 查 Sheets 實際最後一行，
    而非依靠 `old_row_count` 估算。歷史 bug：某次同步寫 70 rows → clear
    A71:K90；下次只寫 40 rows、clear 到 A41:K55，**A56:K70 殘留**。
    新版透過 API 拿到真正 last row，clear 一路到該 row+10、保證無殘留。

    `old_row_count` 參數保留為 fallback（API 查詢失敗時用），既有呼叫不用改。
    """
    sheets_write(token, tab_name, "A1", rows)

    # 查 Sheets 實際 last row（涵蓋所有歷史殘留）。失敗回 0、用 fallback
    try:
        actual_last = sheets_get_last_row(token, tab_name, col=range_prefix)
    except Exception:
        actual_last = 0

    clear_start, clear_end = _compute_clear_range(
        new_rows_count=len(rows),
        actual_last_row=actual_last,
        old_row_count=old_row_count,
    )

    if clear_start <= clear_end:
        try:
            sheets_clear(token, tab_name, f"A{clear_start}:{max_col}{clear_end}")
        except Exception:
            pass  # 殘留行清除失敗不影響資料正確性


def sync_video_overview(token, operator=None):
    """影片總覽分頁：合併影片追蹤 + 數據回填，一個分頁掌握全局。"""
    op = resolve_operator(operator)
    tab_name = get_operator_tabs(op)["video_overview"]
    pipeline_path = os.path.join(PROJECT_ROOT, "data", op, "pipeline.json")

    print(f"  讀取 pipeline shard（{op}）...")
    tracking = get_pipeline_data(pipeline_json=pipeline_path)
    if tracking is None:
        print(f"  ⚠️ 找不到 {os.path.join(PROJECT_ROOT, 'data', op, 'pipeline', '_meta.json')}，略過")
        return

    items = [v for v in tracking.get("items", []) if v.get("vid")]
    perf_thresholds = (
        tracking.get("_meta", {})
        .get("thresholds", {})
        .get("performance")
    )

    try:
        tab_names = sheets_get_tab_names(token)
        if tab_name not in tab_names:
            sheets_add_tab(token, tab_name)
            print(f"  ✅ 建立「{tab_name}」分頁")
    except Exception as e:
        print(f"  ⚠️ 分頁檢查失敗：{e}")

    rows = build_video_overview_rows(items, performance_thresholds=perf_thresholds)
    _write_then_clear(token, tab_name, "A", "K", rows, old_row_count=max(len(items) + 10, 50))

    # Header row (row 0) B1-K1 背景色，每格不同色方便辨別
    # B=待拍(橘) C=已上線(綠) D=留存(藍) E=完播(藍) F-J=需處理(黃/紅) K=更新(灰)
    try:
        header_colors = [
            (0, 1, 1.0, 0.85, 0.6),    # B1 待拍 — 淺橘
            (0, 2, 0.7, 0.93, 0.7),     # C1 已上線 — 淺綠
            (0, 3, 0.73, 0.87, 1.0),    # D1 平均留存 — 淺藍
            (0, 4, 0.73, 0.87, 1.0),    # E1 平均完播 — 淺藍
        ]
        # F 起：需處理項目用淺紅，只對有內容的格子上色
        for col in range(5, 10):
            cell_val = rows[0][col] if col < len(rows[0]) else ""
            if cell_val and "支" in str(cell_val):
                header_colors.append((0, col, 1.0, 0.8, 0.8))   # 淺紅
        header_colors.append((0, 10, 0.92, 0.92, 0.92))  # K1 更新時間 — 灰
        sheets_format_bg(token, tab_name, header_colors)
    except Exception:
        pass  # 格式化失敗不影響資料

    online = sum(1 for v in items if v.get("status") == "已上線")
    pending = sum(1 for v in items if v.get("status") == "待拍")
    print(f"  ✅ 影片總覽（{tab_name}）：{len(items)} 支（已上線 {online} / 待拍 {pending}）")


def sync_inspiration(token, operator=None):
    """靈感庫分頁：智能看板"""
    op = resolve_operator(operator)
    tab_name = get_operator_tabs(op)["inspiration"]
    HEADER_ROWS = 2
    SKIP_TITLES = {"題目", "💡 靈感庫", "💡 靈感庫智能看板", "（靈感庫目前是空的）"}

    print(f"  掃描靈感庫（{op}）...")
    items = scan_inspiration(operator=operator)
    print(f"  找到 {len(items)} 個靈感")

    try:
        tab_names = sheets_get_tab_names(token)
        if tab_name not in tab_names:
            sheets_add_tab(token, tab_name)
            print(f"  ✅ 建立「{tab_name}」分頁")
    except Exception as e:
        print(f"  ⚠️ 分頁檢查失敗：{e}")

    existing = sheets_read(token, tab_name, "A1:G500")
    manual_notes = {}
    for row in existing:
        if not row or not row[0]:
            continue
        title = row[0].strip()
        if title in SKIP_TITLES:
            continue
        note_g = row[6].strip() if len(row) > 6 and row[6] else ""
        note_f = row[5].strip() if len(row) > 5 and row[5] else ""
        note = note_g or note_f
        if note:
            manual_notes[title] = note

    rows = build_inspiration_rows(items)

    if manual_notes:
        for row in rows[HEADER_ROWS:]:
            if row and row[0] in manual_notes:
                row[6] = manual_notes[row[0]]

    old_row_count = max(len(existing) + 5, 50)
    _write_then_clear(token, tab_name, "A", "G", rows, old_row_count=old_row_count)
    preserved = len(manual_notes)
    print(f"  ✅ 靈感庫智能看板（{tab_name}）：寫入 {len(rows)} 行"
          + (f"（保留 {preserved} 筆備註）" if preserved else ""))




def sync_todo(token, operator=None):
    """待辦分頁：智能看板"""
    HEADER_ROWS = 4
    SKIP_TASKS = {"項目", "📋 待辦", "📋 待辦智能看板",
                  "（空）", "（目前沒有工作待辦）", "（目前沒有雜事待辦）"}

    print("  掃描待辦清單...")
    op = resolve_operator(operator)
    work_pending, work_done, misc_pending, misc_done = scan_todos(operator=op)

    existing = sheets_read(token, SH_TODO, "A1:D500")
    manual_notes = {}
    for row in existing:
        if not row or not row[0]:
            continue
        task = row[0].strip()
        if task in SKIP_TASKS or task.startswith("──"):
            continue
        note = row[3].strip() if len(row) > 3 and row[3] else ""
        if note:
            manual_notes[task] = note

    rows = build_todo_rows(work_pending, misc_pending)

    if manual_notes:
        for row in rows[HEADER_ROWS:]:
            if row and row[0] in manual_notes:
                row[3] = manual_notes[row[0]]

    _write_then_clear(token, SH_TODO, "A", "E", rows, old_row_count=max(len(rows) + 5, 35))
    preserved = len(manual_notes)
    print(f"  ✅ 待辦智能看板：工作 {len(work_pending)} 項 + 雜事 {len(misc_pending)} 項未完成"
          + (f"（保留 {preserved} 筆備註）" if preserved else ""))
    return work_pending, work_done, misc_pending, misc_done


def sync_report(token, operator=None):
    """報表分頁：影片產量 + 靈感轉化"""
    print("  建立報表...")
    existing_tabs = sheets_get_tab_names(token)
    if SH_REPORT not in existing_tabs:
        print(f"  「{SH_REPORT}」分頁不存在，自動建立...")
        sheets_add_tab(token, SH_REPORT)
        print(f"  ✅ 已建立「{SH_REPORT}」分頁")

    # 從 sharded pipeline 統計影片產量
    op = resolve_operator(operator)
    pipeline_path = os.path.join(PROJECT_ROOT, "data", op, "pipeline.json")
    tracking = get_pipeline_data(pipeline_json=pipeline_path)
    if tracking is None:
        print("  ❌ pipeline shard 讀取失敗，跳過報表同步")
        return

    now = now_tw()
    month_prefix = now.strftime("%Y-%m")
    week_start = now - timedelta(days=now.weekday())
    week_start_str = week_start.strftime("%Y-%m-%d")

    video_stats = {
        "week_online": 0, "week_editing": 0, "week_shooting": 0,
        "month_online": 0, "month_in_progress": 0,
    }
    for v in tracking.get("items", []):
        if not v.get("vid"):
            continue
        status = v.get("status", "")
        pub = v.get("publish_date", "")
        created = v.get("created_date", "")
        # 本月統計（依建立日或上線日）
        ref_date = pub or created or ""
        if ref_date.startswith(month_prefix):
            if status == "已上線":
                video_stats["month_online"] += 1
            elif status in ("待拍", "剪輯中", "HOLD"):
                video_stats["month_in_progress"] += 1
        # 本週統計（依上線日或建立日）
        if ref_date >= week_start_str:
            if status == "已上線":
                video_stats["week_online"] += 1
            elif status == "剪輯中":
                video_stats["week_editing"] += 1
            elif status == "待拍":
                video_stats["week_shooting"] += 1

    # 靈感統計
    inspiration_items = scan_inspiration(operator=operator)
    insp_stats = {"total": len(inspiration_items), "inbox": 0, "cooldown": 0, "selected": 0}
    for it in inspiration_items:
        if it["status"] in insp_stats:
            insp_stats[it["status"]] += 1

    # 待辦完成統計（從 .md 掃描）
    _wp, work_done, _mp, misc_done = scan_todos(operator=op)
    month_work = sum(1 for d in work_done if (d.get("done_date") or "").startswith(month_prefix))
    month_misc = sum(1 for d in misc_done if (d.get("done_date") or "").startswith(month_prefix))
    week_done = sum(1 for d in work_done + misc_done if (d.get("done_date") or "").lstrip("'") >= week_start_str)
    done_stats = {
        "month_total": month_work + month_misc,
        "month_work": month_work,
        "month_misc": month_misc,
        "week_done": week_done,
    }

    # 載入 weekly_report 以取得豐富指標（表現/開場/CTA/路線對比）
    weekly_data = None
    try:
        ops_lib = os.path.join(PROJECT_ROOT, "scripts", "ops")
        import sys
        if ops_lib not in sys.path:
            sys.path.insert(0, ops_lib)
        from lib.report import weekly_report as _weekly_report
        # pipeline.json 是 SSoT，靈感和影片都在同一份 items 裡
        idea_data = {"items": [it for it in tracking.get("items", []) if not it.get("vid")]}
        weekly_data = _weekly_report(tracking, idea_data)
    except Exception as e:
        print(f"  ⚠️ 無法載入 weekly_report 豐富指標（{e}），使用基礎報表")

    rows = build_report_rows(video_stats, insp_stats, done_stats, weekly_data=weekly_data)

    _write_then_clear(token, SH_REPORT, "A", "D", rows, old_row_count=max(len(rows) + 5, 35))
    print(f"  ✅ 報表：寫入 {len(rows)} 行（本月上線 {video_stats['month_online']} 支）")
