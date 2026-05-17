#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crew 日報子系統：初始化 / 填報 / 看板 / 分析 / 歸檔。
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, date

from .config import (
    PROJECT_ROOT, TW_TZ, SPREADSHEET_ID,
    SH_EMPLOYEE_LOG, LOG_SEPARATOR_ROW,
    LOG_HEADER_ROW, LOG_DATA_START_ROW,
    SHEETS_API,
)
from .sheets_api import (
    sheets_write, sheets_read, sheets_append, sheets_clear,
    sheets_get_tab_names, sheets_add_tab, sheets_delete_tab,
    sheets_set_validation, _sheets_request,
)
from .scanners import now_tw


# ── 基礎類別清單（永不刪除，只能新增）───────────────
_BASE_CATEGORIES = ["拍攝", "剪輯", "企劃", "行政", "其他"]
_SHEETS_READ_RANGE = 2000  # 讀取上限，超過 1500 行時警告
_SHEETS_WARN_THRESHOLD = 1500


def _auto_evolve_categories(data):
    """
    自我升級類別清單：出現 ≥ 2 次的新類別自動升格。
    回傳 (完整類別清單, 本次新發現的類別列表)。
    """
    counts = Counter(
        d["category"] for d in data
        if d["category"] and d["category"] not in ("未分類", "")
    )
    evolved = list(_BASE_CATEGORIES)
    new_cats = []
    for cat, cnt in counts.most_common():
        if cat not in evolved and cnt >= 2:
            evolved.append(cat)
            new_cats.append(cat)
    return evolved, new_cats


# ── 解析 Sheets 原始資料 ─────────────────────────────

def _parse_employee_rows(raw_rows):
    """
    解析日報原始 Sheets 資料為 dict list。
    自動相容三個版本 layout。
    """
    def row_val(i):
        return (raw_rows[i][0] if len(raw_rows) > i and raw_rows[i] else "").strip()

    if row_val(LOG_DATA_START_ROW - 2) == "日期":   # index 5 = 行 6
        start = LOG_DATA_START_ROW - 1              # index 6 = 行 7
    elif row_val(1) == "日期":
        start = 2
    elif row_val(0) == "日期":
        start = 1
    else:
        start = LOG_DATA_START_ROW - 1

    data = []
    for row in raw_rows[start:]:
        if not row or not any((cell or "").strip() for cell in row):
            continue
        date_raw = (row[0] or "").lstrip("'").strip()
        name     = (row[1] or "").strip() if len(row) > 1 else ""
        if not date_raw or not name:
            continue
        # 正規化日期：支援 M/D、MM/DD → YYYY-MM-DD
        if "/" in date_raw:
            parts = date_raw.split("/")
            if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]) and int(parts[0]) > 12:
                date_raw = f"{int(parts[0])}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            elif len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                y = now_tw().year
                date_raw = f"{y}-{int(parts[0]):02d}-{int(parts[1]):02d}"
        # 跳過看板殘留列
        if len(date_raw) < 10 or date_raw[4] != "-" or date_raw[7] != "-":
            continue
        try:
            datetime.strptime(date_raw[:10], "%Y-%m-%d")
        except ValueError:
            continue
        date_raw = date_raw[:10]
        data.append({
            "date":     date_raw,
            "name":     name,
            "completed":  (row[2] or "").strip() if len(row) > 2 else "",
            "in_progress": (row[3] or "").strip() if len(row) > 3 else "",
            # 向下相容舊格式
            "category": (row[2] or "").strip() if len(row) > 2 else "",
            "task":     (row[3] or "").strip() if len(row) > 3 else "",
            "duration": (row[4] or "").strip() if len(row) > 4 else "",
        })
    return data


def _extract_output_count(text):
    """從文字中提取產出數量：'剪完2支' → 2, '完成1支 粗剪1支' → 2"""
    import re
    # 阿拉伯數字
    nums = re.findall(r'(\d+)\s*支', text)
    total = sum(int(n) for n in nums)
    # 中文數字
    cn_map = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    for cn, val in cn_map.items():
        if cn in text and f"{cn}支" not in "".join(nums):
            if re.search(rf'{cn}[部支]', text):
                total += val
    return total if total > 0 else (1 if text.strip() else 0)


# ── 看板 ─────────────────────────────────────────────

def _build_dashboard_rows(data, now_dt):
    """v5.0 產出導向看板：4 行智能摘要。"""
    week_start    = (now_dt - timedelta(days=now_dt.weekday())).strftime("%Y-%m-%d")
    lw_start      = (now_dt - timedelta(days=now_dt.weekday() + 7)).strftime("%Y-%m-%d")
    lw_end        = (now_dt - timedelta(days=now_dt.weekday() + 1)).strftime("%Y-%m-%d")
    cut30         = (now_dt - timedelta(days=30)).strftime("%Y-%m-%d")

    all_members = sorted(set(d["name"] for d in data if d["date"] >= cut30))
    week_data   = [d for d in data if d["date"] >= week_start]
    lw_data     = [d for d in data if lw_start <= d["date"] <= lw_end]

    # 計算本週完成數
    week_completed = sum(_extract_output_count(d.get("completed", d.get("task", ""))) for d in week_data)
    lw_completed = sum(_extract_output_count(d.get("completed", d.get("task", ""))) for d in lw_data)
    work_days = max(1, len(set(d["date"] for d in week_data))) if week_data else 1
    daily_avg = round(week_completed / work_days, 1)

    t_delta = week_completed - lw_completed
    t_trend = (f"↑{t_delta}" if t_delta > 0 else f"↓{abs(t_delta)}" if t_delta < 0 else "→") if lw_completed > 0 else ""

    # 行 1：週產出
    row1 = [
        "📊 週產出",
        f"完成 {week_completed} 支 {t_trend}",
        f"日均 {daily_avg} 支",
        f"更新：{now_dt.strftime('%m/%d %H:%M')}",
    ]

    # 行 2：進行中（取最近一筆的 in_progress）
    latest_ip = ""
    for d in reversed(data):
        ip = d.get("in_progress", "").strip()
        if ip:
            latest_ip = ip
            break
    row2 = ["📋 進行中", latest_ip if latest_ip else "（無）", "", ""]

    # 行 3：各人產出
    week_parts = []
    for m in all_members:
        m_w = [d for d in week_data if d["name"] == m]
        if not m_w:
            week_parts.append(f"{m}: 0支")
            continue
        m_completed = sum(_extract_output_count(d.get("completed", d.get("task", ""))) for d in m_w)
        days = len(set(d["date"] for d in m_w))
        week_parts.append(f"{m}: 完成{m_completed}支 填{days}天")
    row3 = ["👤 各人", "  |  ".join(week_parts) if week_parts else "（本週無記錄）", "", ""]

    # 行 4：異常
    anomalies = []
    for m in all_members:
        consec = 0
        chk = now_dt - timedelta(days=1)
        for _ in range(7):
            if any(d["name"] == m and d["date"] == chk.strftime("%Y-%m-%d") for d in data):
                break
            consec += 1
            chk -= timedelta(days=1)
        if consec >= 3:
            anomalies.append(f"🔴 {m} 連{consec}天未填")
        elif consec >= 2:
            anomalies.append(f"⚠️ {m} {consec}天未填")

    if anomalies:
        row4 = ["⚠️ 異常", "  |  ".join(anomalies), "", ""]
    else:
        row4 = ["✅ 異常", "無", "", ""]

    return [row1, row2, row3, row4]


def _write_dashboard(token, data, now_dt):
    """將 4 行看板寫入 Sheets 行 1-4。"""
    try:
        rows = _build_dashboard_rows(data, now_dt)
        sheets_clear(token, SH_EMPLOYEE_LOG, "A1:D4")
        sheets_write(token, SH_EMPLOYEE_LOG, "A1", rows)
    except Exception as e:
        print(f"  ⚠️ 看板寫入失敗：{e}")


# ── 填報 ─────────────────────────────────────────────

def append_employee_log(token, name, category="", task="", duration="", note="",
                        completed="", in_progress=""):
    """新增一筆日報記錄。支援新格式(completed/in_progress)和舊格式(category/task/duration)。"""
    today = now_tw().strftime("%Y-%m-%d")
    if completed or in_progress:
        # v5.0 新格式：4 欄
        row = [["'" + today, name, completed, in_progress]]
        sheets_append(token, SH_EMPLOYEE_LOG, row)
        print(f"  ✅ 已寫入日報：{today} | {name} | 完成: {completed} | 進行中: {in_progress}")
    else:
        # 舊格式相容
        row = [["'" + today, name, category, task, duration, note]]
        sheets_append(token, SH_EMPLOYEE_LOG, row)
        print(f"  ✅ 已寫入日報：{today} | {name} | {category} | {task} | {duration}")
    _refresh_a1_after_log(token, name, completed or category, task)


def _refresh_a1_after_log(token, name, category, task):
    """填報後即時刷新看板行 1-4。"""
    try:
        now  = now_tw()
        rows = sheets_read(token, SH_EMPLOYEE_LOG, f"A1:F{_SHEETS_READ_RANGE}")
        data = _parse_employee_rows(rows) if rows else []
        _write_dashboard(token, data, now)
    except Exception:
        pass


# ── 初始化 ───────────────────────────────────────────

def init_employee_log(token):
    """v4.0 日報看板初始化。"""
    print("  檢查並清理舊分頁...")
    now       = now_tw()
    all_tabs  = sheets_get_tab_names(token)

    if "團隊日報" in all_tabs:
        deleted = sheets_delete_tab(token, "團隊日報")
        print(f"  {'✅ 已刪除「團隊日報」分頁' if deleted else '⚠️ 「團隊日報」刪除失敗'}")

    if SH_EMPLOYEE_LOG not in all_tabs:
        print(f"  「{SH_EMPLOYEE_LOG}」不存在，建立中...")
        sheets_add_tab(token, SH_EMPLOYEE_LOG)
        all_rows  = []
        data_rows = []
    else:
        print("  分頁已存在，偵測格式...")
        all_rows = sheets_read(token, SH_EMPLOYEE_LOG, f"A1:F{_SHEETS_READ_RANGE}") or []

        def row_val(i):
            return (all_rows[i][0] if len(all_rows) > i and all_rows[i] else "").strip()

        if row_val(5) == "日期":
            print("  已是 v4.0 看板格式，刷新看板區...")
            data = _parse_employee_rows(all_rows)
            _write_dashboard(token, data, now)
            print("  ✅ 看板已刷新（行 1-4）")
            separator_row = ["─── 填報區 ───", "", "", ""]
            header_row    = ["日期", "姓名", "完成", "進行中"]
            sheets_write(token, SH_EMPLOYEE_LOG, f"A{LOG_SEPARATOR_ROW}", [separator_row, header_row])
            print(f"  ✅ 分隔線（行 {LOG_SEPARATOR_ROW}）＋標頭（行 {LOG_HEADER_ROW}）已更新")
            _finalize_init(token, data)
            return
        elif row_val(1) == "日期":
            print("  偵測到 v3.x 格式（行 2 = 標頭），遷移至 v4.0...")
            data_rows = [r for r in all_rows[2:] if r and any((c or "").strip() for c in r)]
        elif row_val(0) == "日期":
            print("  偵測到超舊版格式（行 1 = 標頭），遷移至 v4.0...")
            data_rows = [r for r in all_rows[1:] if r and any((c or "").strip() for c in r)]
        else:
            print("  格式不明，嘗試抽取資料列...")
            data_rows = []
            for r in all_rows:
                if not r or not any((c or "").strip() for c in r):
                    continue
                v = (r[0] or "").lstrip("'").strip()
                if v == "日期" or v.startswith("（") or not v:
                    continue
                if len(v) >= 8 and (v[4] == "-" or v[4].isdigit()):
                    data_rows.append(r)
            print(f"  抽取到 {len(data_rows)} 筆資料列")

    parsed_data = []
    for r in data_rows:
        date_raw = (r[0] or "").lstrip("'").strip()
        name     = (r[1] or "").strip()
        if not date_raw or not name:
            continue
        parsed_data.append({
            "date":     date_raw,
            "name":     name,
            "category": (r[2] or "").strip() if len(r) > 2 else "",
            "task":     (r[3] or "").strip() if len(r) > 3 else "",
            "duration": (r[4] or "").strip() if len(r) > 4 else "",
        })

    dashboard = _build_dashboard_rows(parsed_data, now)

    separator_row = [
        "─── 填報區（往下新增列，請勿修改上方看板）───",
        "", "", "", "", ""
    ]
    header_row = ["日期", "姓名", "類別", "做了什麼", "花多久", "備註"]

    new_layout = dashboard + [separator_row, header_row] + data_rows

    while len(new_layout) < 500:
        new_layout.append(["", "", "", "", "", ""])

    sheets_write(token, SH_EMPLOYEE_LOG, "A1", new_layout)
    print(f"  ✅ v4.0 看板寫入完成（{len(data_rows)} 筆資料移至行 {LOG_DATA_START_ROW} 起）")

    _finalize_init(token, parsed_data)


def _finalize_init(token, data=None):
    """初始化收尾。v5.0 不再設定下拉選單（C 欄改為自由文字）。"""
    print("\n  ✅ 日報初始化完成（v5.0 產出看板）")
    print(f"  👉 Crew填寫網址：https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"\n  填寫說明（從第 {LOG_DATA_START_ROW} 列開始填，不要動上方看板）：")
    print("    A 日期    → YYYY-MM-DD（如 2026-03-04）")
    print("    B 姓名    → Crew名字")
    print("    C 類別    → 下拉選單（可填新類別，系統自動學習 ≥2 次升格）")
    print("    D 做了什麼 → 一句話描述")
    print("    E 花多久  → 如 1hr、0.5hr")
    print("    F 備註    → 選填")


# ── 分析 ─────────────────────────────────────────────

def _build_period_analysis(data, period_start, period_end, label="",
                            ref_start=None, ref_end=None):
    """計算指定時段的Crew統計摘要，回傳格式化 Markdown 文字。"""
    def in_range(d, s, e):
        return s <= d["date"] <= e

    target = [d for d in data if in_range(d, period_start, period_end)]
    ref    = [d for d in data if ref_start and ref_end
              and in_range(d, ref_start, ref_end)]

    all_members = sorted(set(
        d["name"] for d in (target if target else ref)
    ))
    if not all_members:
        return "（本期無日報記錄）\n"

    team_total = len(target)
    ref_total  = len(ref)
    lines = []

    lines.append(f"## 📊 {label} 團隊總覽\n")
    t_delta = team_total - ref_total
    t_trend = (f"（對比上期 {'↑' if t_delta>0 else '↓' if t_delta<0 else '→'}"
               f"{abs(t_delta)}）") if ref_total > 0 else ""
    lines.append(f"- 總任務數：{team_total} 件 {t_trend}\n")

    actual_fill_pd  = len(set((d["name"], d["date"]) for d in target))
    unique_dates    = len(set(d["date"] for d in target)) or 1
    expect_pd       = len(all_members) * unique_dates
    fill_rate_pct   = int(actual_fill_pd / expect_pd * 100) if expect_pd > 0 else 0
    lines.append(f"- 填報率：{fill_rate_pct}%\n")

    team_cats = defaultdict(int)
    for d in target:
        team_cats[d["category"] or "未分類"] += 1
    if team_cats and team_total > 0:
        cat_str = " | ".join(
            f"{cat} {int(c/team_total*100)}%"
            for cat, c in sorted(team_cats.items(), key=lambda x: -x[1])
        )
        lines.append(f"- 類別分佈：{cat_str}\n")
    lines.append("\n")

    anomalies = []
    avg = team_total / len(all_members) if all_members else 0

    for member in all_members:
        m_target = [d for d in target if d["name"] == member]
        m_ref    = [d for d in ref    if d["name"] == member]
        m_total  = len(m_target)
        m_ref_t  = len(m_ref)
        m_share  = f"{int(m_total/team_total*100)}%" if team_total > 0 else "—"
        m_days   = len(set(d["date"] for d in m_target))

        m_delta  = m_total - m_ref_t
        m_trend  = (f" ↑{m_delta}" if m_delta > 0 else
                    f" ↓{abs(m_delta)}" if m_delta < 0 else " →") if m_ref_t > 0 else ""

        m_cats = defaultdict(int)
        for d in m_target:
            m_cats[d["category"] or "未分類"] += 1
        cat_str = " | ".join(
            f"{cat} {int(c/m_total*100)}%"
            for cat, c in sorted(m_cats.items(), key=lambda x: -x[1])
        ) if m_total > 0 else "無記錄"

        lines.append(f"### 👤 {member}（{m_total} 件，佔 {m_share}）{m_trend}\n")
        lines.append(f"- 填報：{m_days} 天　類別：{cat_str}\n")

        for d in m_target[:25]:
            day     = d["date"][5:] if len(d["date"]) >= 7 else d["date"]
            dur_str = f" | {d['duration']}" if d["duration"] else ""
            lines.append(f"  - {day} | {d['category']} | {d['task']}{dur_str}\n")
        if len(m_target) > 25:
            lines.append(f"  ...（共 {len(m_target)} 筆，僅顯示前 25）\n")
        lines.append("\n")

        if len(all_members) > 1:
            if m_total > avg * 1.5 and m_total > 3:
                anomalies.append(
                    f"- ⚠️ {member} 工作量偏高（{m_total} 件，均值 {int(avg)} 件）建議分擔")
            elif team_total >= 6 and m_total < avg * 0.4:
                anomalies.append(
                    f"- ⚠️ {member} 工作量偏低（{m_total} 件，均值 {int(avg)} 件）")
        admin = m_cats.get("行政", 0)
        if m_total >= 3 and admin / m_total > 0.4:
            anomalies.append(
                f"- ⚠️ {member} 行政任務佔 {int(admin/m_total*100)}%，注意是否擠壓創作時間")

    if anomalies:
        lines.append("## 🔔 異常旗標\n")
        lines.extend(a + "\n" for a in anomalies)
        lines.append("\n")

    return "".join(lines)


def analyze_employee_data(token, target_date_str=None):
    """即時智能分析日報。"""
    print("  讀取日報...")
    rows = sheets_read(token, SH_EMPLOYEE_LOG, f"A1:F{_SHEETS_READ_RANGE}")
    if not rows or len(rows) <= 1:
        print("  （日報目前無資料，無法分析）")
        return
    if len(rows) >= _SHEETS_WARN_THRESHOLD:
        print(f"  ⚠️ 日報已有 {len(rows)} 行（接近上限 {_SHEETS_READ_RANGE}），建議盡快說「整理日報」歸檔")

    data = _parse_employee_rows(rows)
    if not data:
        print("  （日報目前無資料）")
        return

    now       = now_tw()
    today_str = target_date_str or now.strftime("%Y-%m-%d")
    try:
        today_dt = datetime.fromisoformat(today_str).replace(tzinfo=TW_TZ)
    except ValueError:
        today_dt  = now
        today_str = now.strftime("%Y-%m-%d")

    yesterday_str  = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    week_start_str = (today_dt - timedelta(days=today_dt.weekday())).strftime("%Y-%m-%d")
    lw_start_str   = (today_dt - timedelta(days=today_dt.weekday() + 7)).strftime("%Y-%m-%d")
    lw_end_str     = (today_dt - timedelta(days=today_dt.weekday() + 1)).strftime("%Y-%m-%d")

    cut30 = (today_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    all_members = sorted(set(d["name"] for d in data if d["date"] >= cut30))
    if not all_members:
        print("  （近 30 天無日報記錄）")
        return

    print(f"\n=== 日報分析 | {today_str} ===\n")

    # 昨日情況
    print(f"📋 昨日（{yesterday_str}）")
    for member in all_members:
        entries = [d for d in data if d["name"] == member and d["date"] == yesterday_str]
        if entries:
            cats = " | ".join(dict.fromkeys(
                e["category"] for e in entries if e["category"]
            ))
            print(f"  ✅ {member}：{len(entries)} 項{f'（{cats}）' if cats else ''}")
        else:
            consecutive = 0
            check = today_dt - timedelta(days=1)
            for _ in range(7):
                cs = check.strftime("%Y-%m-%d")
                if any(d["name"] == member and d["date"] == cs for d in data):
                    break
                consecutive += 1
                check -= timedelta(days=1)
            warn = f"  （⚠️ 已連續 {consecutive} 天未填）" if consecutive >= 2 else ""
            print(f"  ❌ {member}：未填{warn}")

    # 本週統計
    print(f"\n📊 本週（{week_start_str} ～ {today_str}）")

    def pstats(member, s, e):
        rows_in = [d for d in data if d["name"] == member and s <= d["date"] <= e]
        cats = defaultdict(int)
        fill_dates = set()
        for r in rows_in:
            cats[r["category"] or "未分類"] += 1
            fill_dates.add(r["date"])
        return len(rows_in), len(fill_dates), dict(cats)

    week_stats = {m: pstats(m, week_start_str, today_str) for m in all_members}
    lw_stats   = {m: pstats(m, lw_start_str,   lw_end_str) for m in all_members}
    team_week  = sum(s[0] for s in week_stats.values())
    team_lw    = sum(s[0] for s in lw_stats.values())

    for member in all_members:
        total, fill_days, cats = week_stats[member]
        lw_total = lw_stats[member][0]
        share    = f"{int(total/team_week*100)}%" if team_week > 0 else "—"
        delta    = total - lw_total
        trend    = (f" ↑{delta}" if delta > 0 else
                    f" ↓{abs(delta)}" if delta < 0 else " →") if lw_total > 0 else ""
        cat_str  = " | ".join(
            f"{cat} {int(c/total*100)}%"
            for cat, c in sorted(cats.items(), key=lambda x: -x[1])
        ) if total > 0 else "無記錄"
        print(f"  {member}：{total} 項（佔 {share}）{trend}　填 {fill_days} 天")
        print(f"         類別：{cat_str}")

    t_delta = team_week - team_lw
    t_trend = (f"（上週 {team_lw} {'↑' if t_delta>0 else '↓' if t_delta<0 else '→'}"
               f"{abs(t_delta)}）") if team_lw > 0 else ""
    print(f"\n  團隊共 {team_week} 項 {t_trend}")

    # 異常偵測
    anomalies = []
    avg = team_week / len(all_members) if all_members else 0

    for member in all_members:
        consecutive = 0
        check = today_dt - timedelta(days=1)
        for _ in range(7):
            cs = check.strftime("%Y-%m-%d")
            if any(d["name"] == member and d["date"] == cs for d in data):
                break
            consecutive += 1
            check -= timedelta(days=1)
        if consecutive >= 2:
            anomalies.append(f"⚠️ {member} 連續 {consecutive} 天未填日報")
        if len(all_members) > 1:
            total = week_stats[member][0]
            if total > avg * 1.5 and total > 3:
                anomalies.append(
                    f"⚠️ {member} 工作量偏高（{total} 項，均值 {int(avg)} 項）建議分擔")
            elif team_week >= 6 and total < avg * 0.4:
                anomalies.append(
                    f"⚠️ {member} 工作量偏低（{total} 項，均值 {int(avg)} 項）")
        total, _, cats = week_stats[member]
        admin = cats.get("行政", 0)
        if total >= 3 and admin / total > 0.4:
            anomalies.append(
                f"⚠️ {member} 行政任務佔 {int(admin/total*100)}%，注意是否擠壓創作時間")

    if anomalies:
        print("\n🔔 異常偵測")
        for a in anomalies:
            print(f"  {a}")
    else:
        print("\n✅ 本週無異常")

    print("\n=== END ===")

    try:
        evolved_cats, new_cats = _auto_evolve_categories(data)
        if new_cats:
            ok = sheets_set_validation(token, SH_EMPLOYEE_LOG, evolved_cats)
            if ok:
                print(f"\n🔄 類別自動升級：新增 {new_cats} → 下拉選單已更新（共 {len(evolved_cats)} 個類別）")
            else:
                print(f"\n⚠️ 偵測到新類別 {new_cats}，但下拉選單更新失敗")
    except Exception:
        pass

    _write_dashboard(token, data, now)


# ── 歸檔 ─────────────────────────────────────────────

def archive_employee(token):
    """整理日報：輸出週報 .md + 刪除 Sheets 資料行 + 刷新 Dashboard"""
    import urllib.request as _ur

    print("  讀取日報...")
    rows = sheets_read(token, SH_EMPLOYEE_LOG, f"A1:F{_SHEETS_READ_RANGE}")
    if not rows:
        print("  （日報目前無資料）")
        return

    data_rows = []
    for i, row in enumerate(rows):
        if i < LOG_DATA_START_ROW - 1:
            continue
        if not any((cell.strip() if cell else "") for cell in row):
            continue
        data_rows.append((i, row))

    if not data_rows:
        print("  ✅ 日報沒有資料，無需整理")
        return

    if len(rows) >= _SHEETS_WARN_THRESHOLD:
        print(f"  ⚠️ 日報已有 {len(rows)} 行（接近上限 {_SHEETS_READ_RANGE}），歸檔後將清空")

    print(f"  找到 {len(data_rows)} 筆記錄，開始歸檔...")

    # ── JSON 備份（在刪除 Sheets 之前，確保可恢復）──
    backup_dir = os.path.join(PROJECT_ROOT, "data", "employee-backup")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"{now_tw().strftime('%Y-%m-%d')}.json")
    backup_data = [row for _, row in data_rows]
    with open(backup_path, "w", encoding="utf-8") as bf:
        json.dump(backup_data, bf, ensure_ascii=False, indent=2)
    print(f"  💾 備份已寫入：{backup_path}（{len(backup_data)} 筆）")

    current_year = now_tw().year
    validation_errors = []
    for row_idx, row in data_rows:
        sheet_row = row_idx + 1
        date_raw = (row[0] if row else "").strip()
        name_raw = (row[1] if len(row) > 1 else "").strip()
        if not date_raw:
            validation_errors.append(f"    ⚠️ 第 {sheet_row} 行：日期為空")
        if not name_raw:
            validation_errors.append(f"    ⚠️ 第 {sheet_row} 行：姓名為空")
    if validation_errors:
        print("  ⚠️ 格式問題（以下行可能被歸入「未知」週）：")
        for err in validation_errors:
            print(err)
        print()

    weekly = defaultdict(list)

    def _parse_date_to_iso(date_raw):
        date_raw = date_raw.lstrip("'").strip()
        if len(date_raw) >= 10 and "-" in date_raw[:7]:
            return date_raw[:10]
        elif "/" in date_raw:
            parts = date_raw.split("/")
            if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]) and int(parts[0]) > 12:
                return f"{int(parts[0])}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            elif len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                m, d_val = int(parts[0]), int(parts[1])
                return f"{current_year}-{m:02d}-{d_val:02d}"
        return None

    def _iso_week_label(iso_date_str):
        try:
            dt = date.fromisoformat(iso_date_str)
            iso_year, iso_week, _ = dt.isocalendar()
            month = dt.month
            return (iso_date_str[:7], iso_week), f"{dt.year}-{month:02d}-W{iso_week}"
        except ValueError:
            return ("未知", 0), "未知"

    skipped_dates = []
    _week_sort_keys = {}
    for row_idx, row in data_rows:
        date_raw = row[0] if row else ""
        iso_date = _parse_date_to_iso(date_raw)
        if iso_date:
            sort_key, week_label = _iso_week_label(iso_date)
        else:
            sort_key, week_label = ("未知", 0), "未知"
            if date_raw.strip():
                skipped_dates.append(f"    ⚠️ 第 {row_idx + 1} 行：日期「{date_raw.strip()}」無法解析（需 YYYY-MM-DD 或 M/D 格式）")
        _week_sort_keys[week_label] = sort_key
        weekly[week_label].append(row)

    if skipped_dates:
        print("  ⚠️ 以下日期無法解析，已歸入「未知」週：")
        for msg in skipped_dates:
            print(msg)
        print()

    report_dir = os.path.join(PROJECT_ROOT, "00-control-center", "employee-reports")
    os.makedirs(report_dir, exist_ok=True)

    # 按 sort_key（(year-month, week_num)）排序，而非字串排序
    written_reports = []
    for week_label, week_rows in sorted(weekly.items(),
                                         key=lambda x: _week_sort_keys.get(x[0], (x[0], 0))):
        by_person = defaultdict(list)
        for row in week_rows:
            name = row[1] if len(row) > 1 else "未知"
            by_person[name].append(row)

        total_entries = len(week_rows)

        dates_in_week = []
        for row in week_rows:
            d = _parse_date_to_iso(row[0] if row else "")
            if d:
                dates_in_week.append(d)
        dates_in_week.sort()
        period_start = dates_in_week[0] if dates_in_week else f"{current_year}-01-01"
        period_end = dates_in_week[-1] if dates_in_week else f"{current_year}-12-31"
        date_range_str = f"{period_start} ~ {period_end}" if dates_in_week else week_label

        fake_hdr = [["日期","姓名","類別","做了什麼","花多久","備註"]]
        week_data_p = _parse_employee_rows(fake_hdr + list(week_rows))
        analysis_text = _build_period_analysis(
            week_data_p, period_start, period_end, label=f"{week_label} 週報"
        )

        md_lines = [
            f"# {week_label} 日報週報\n\n",
            f"> 整理時間：{now_tw().strftime('%Y-%m-%d %H:%M')}"
            f"　期間：{date_range_str}　共 {total_entries} 筆\n\n",
            analysis_text,
            "---\n\n",
            "## 📋 原始明細\n\n",
        ]
        for person, person_rows in sorted(by_person.items()):
            md_lines.append(f"### {person}\n\n")
            for row in person_rows:
                d_val = row[0].lstrip("'") if len(row) > 0 else ""
                cat  = row[2] if len(row) > 2 else ""
                task = row[3] if len(row) > 3 else ""
                dur  = row[4] if len(row) > 4 else ""
                note = row[5] if len(row) > 5 else ""
                day  = d_val[5:] if len(d_val) >= 7 else d_val
                note_str = f"（{note}）" if note.strip() else ""
                md_lines.append(f"- {day} | {cat} | {task} | {dur}{note_str}\n")
            md_lines.append("\n")

        report_path = f"{report_dir}/{week_label}_日報週報.md"
        if os.path.exists(report_path):
            print(f"  ⚠️ {report_path} 已存在，將覆蓋（舊版保留在 git history）")
        with open(report_path, "w", encoding="utf-8") as f:
            f.writelines(md_lines)
        written_reports.append(report_path)
        print(f"  ✅ 週報輸出：{report_path}")

    # 刪除 Sheets 資料行
    print("  清除 Sheets 資料行...")
    url = f"{SHEETS_API}/{SPREADSHEET_ID}?fields=sheets.properties"
    req = _ur.Request(url, headers={"Authorization": f"Bearer {token}"})
    meta = _sheets_request(req)
    sheet_id = None
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == SH_EMPLOYEE_LOG:
            sheet_id = s["properties"]["sheetId"]
            break

    if sheet_id is not None:
        requests = []
        for row_idx, _ in sorted(data_rows, key=lambda x: x[0], reverse=True):
            requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_idx,
                        "endIndex": row_idx + 1
                    }
                }
            })
        url = f"{SHEETS_API}/{SPREADSHEET_ID}:batchUpdate"
        body = json.dumps({"requests": requests}).encode("utf-8")
        req = _ur.Request(url, data=body, method="POST",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        _sheets_request(req)
        print(f"  ✅ 已刪除 {len(data_rows)} 筆資料行")

    try:
        _write_dashboard(token, [], now_tw())
        print("  ✅ Dashboard 已歸零")
    except Exception as e:
        print(f"  ⚠️ Dashboard 刷新失敗：{e}")

    print("\n  📋 整理完成：")
    print(f"    - 歸檔：{len(data_rows)} 筆")
    print(f"    - 週報：{', '.join(written_reports)}")
    print("    - Sheets：已清空，可開始新一週填報")
