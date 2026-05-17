#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各分頁 row builders：靈感庫 / 數據回填 / 待辦 / 報表。
"""


from datetime import datetime, timedelta

from .config import classify_performance_display
from .scanners import now_tw, as_text_date


# ── 靈感庫 ────────────────────────────────────────────

def build_inspiration_rows(items):
    """建立靈感庫分頁（智能看板）：漏斗摘要 + 停留天數 + 緊急旗標"""
    now = now_tw()
    today = now.date()

    status_icon = {
        "inbox":    "📥",
        "cooldown": "❄️",
        "selected": "🎯",
        "converted": "🎬",
        "archived": "📦",
    }

    counts = {"inbox": 0, "cooldown": 0, "selected": 0, "converted": 0, "archived": 0}
    stale_count = 0

    def _age_days(item):
        d = item.get("date", "")
        if not d:
            return 0
        try:
            added = datetime.strptime(d, "%Y-%m-%d").date()
            return max(0, (today - added).days)
        except ValueError:
            return 0

    for it in items:
        s = it.get("status", "inbox")
        counts[s] = counts.get(s, 0) + 1
        if s == "inbox" and _age_days(it) >= 7:
            stale_count += 1

    total = len(items)
    selected_count = counts["selected"]
    conv_rate = (f"{int(selected_count / total * 100)}%"
                 if total > 0 else "N/A")

    rows = [
        [f"📥 inbox: {counts['inbox']}",
         f"❄️ cooldown: {counts['cooldown']}",
         f"🎯 selected: {selected_count}",
         f"轉化率(selected/total): {conv_rate}", "",
         "", f"更新：{now.strftime('%Y-%m-%d %H:%M')}"],
        ["題目", "標籤", "加入日期", "狀態", "停留天數", "緊急旗標", "備註"],
    ]

    def _urgency(item):
        s = item.get("status", "inbox")
        if s == "inbox":
            age = _age_days(item)
            if age >= 14:
                return "🔴 超過14天"
            elif age >= 7:
                return "⚠️ 需整理"
            else:
                return "（新）"
        elif s == "cooldown":
            return "❄️ 待觀察"
        elif s == "selected":
            return "🎯 進行中"
        elif s == "converted":
            return "🎬 已轉影片"
        elif s == "archived":
            return "📦 已封存"
        return ""

    if not items:
        rows.append(["（靈感庫目前是空的）", "", "", "", "", "", ""])
    else:
        order = {"inbox": 0, "cooldown": 1, "selected": 2, "converted": 3, "archived": 4}

        def _sort_key(it):
            s_order = order.get(it.get("status", "inbox"), 9)
            age = _age_days(it) if it.get("status") == "inbox" else 0
            return (s_order, -age)

        for it in sorted(items, key=_sort_key):
            age = _age_days(it)
            rows.append([
                it["title"],
                it.get("tag", ""),
                it.get("date", ""),
                status_icon.get(it.get("status", "inbox"), it.get("status", "")),
                str(age) if it.get("date") else "",
                _urgency(it),
                "",
            ])

    return rows


# ── 影片總覽（合併影片追蹤 + 數據回填）─────────────────

def build_video_overview_rows(items, performance_thresholds=None):
    """建立影片總覽分頁：所有影片一覽，含狀態、表現、下一步。

    Args:
        items: pipeline.json 的 items list（所有有 vid 的 item）
    """
    now = now_tw()
    today = now.date()

    def _days_since(date_str):
        if not date_str:
            return 0
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            return max(0, (today - d).days)
        except ValueError:
            return 0

    def _view_str(views):
        try:
            v = int(views or 0)
            if v >= 10000:
                return f"{v/10000:.1f}萬"
            return str(v) if v > 0 else "—"
        except (TypeError, ValueError):
            return "—"

    def _infer_post_type(bf):
        diag = bf.get("diagnosis") or {}
        pt = diag.get("post_type")
        if pt:
            return pt
        eng = 0
        try:
            eng = float(bf.get("engagement_rate", 0) or 0)
        except (TypeError, ValueError):
            pass
        if eng >= 3.0:
            return "互動型（推估）"
        elif eng >= 1.5:
            return "按讚型（推估）"
        elif eng > 0:
            return "低互動（推估）"
        return "待補數據"

    def _weaknesses_str(bf):
        diag = bf.get("diagnosis") or {}
        weak = diag.get("weaknesses") or []
        return ", ".join(weak) if weak else "✅ 無明顯弱點"

    def _next_action(v):
        status = v.get("status", "")
        if status == "待拍":
            has_script = bool(v.get("script_path"))
            days = _days_since(v.get("created_date"))
            if not has_script:
                return "📝 需寫腳本"
            elif days > 30:
                return "⚠️ 卡太久，要拍還是歸檔？"
            elif days > 7:
                return f"⏰ 等待中（{days}天）"
            else:
                return "✅ 可以拍"
        elif status == "剪輯中":
            return "✂️ 剪輯中"
        elif status == "已上線":
            bf = v.get("backfill")
            if not bf:
                return "📊 需回填數據"
            missing = [f for f in ["likes", "comments", "shares", "saves"]
                       if bf.get(f) is None]
            if missing:
                return "📌 需補 " + "/".join(missing)
            return "✅ 完成"
        return status

    # Build enriched rows
    enriched = []
    for v in items:
        if not v.get("vid"):
            continue
        status = v.get("status", "")
        bf = v.get("backfill") or {}
        days = _days_since(v.get("created_date") if status == "待拍" else None)

        # Status display with days
        if status == "待拍":
            if days > 30:
                status_display = f"🔴 待拍 {days}天"
            elif days > 7:
                status_display = f"🟠 待拍 {days}天"
            else:
                status_display = f"🟡 待拍 {days}天"
        elif status == "剪輯中":
            status_display = "🔵 剪輯中"
        elif status == "已上線":
            status_display = "🟢 已上線"
        else:
            status_display = status

        # Performance tier
        if bf and bf.get("views") is not None:
            tier = classify_performance_display(
                bf.get("views", 0), bf.get("retention_3s", 0),
                bf.get("completion_rate", 0),
                thresholds=performance_thresholds,
            )
        else:
            tier = "—"

        next_action = _next_action(v)

        # Sort: 已上線 on top (newest first), then 剪輯中, then 待拍 (longest wait first)
        if status == "已上線":
            sort_group = 0
        elif status == "剪輯中":
            sort_group = 1
        else:
            sort_group = 2

        enriched.append({
            "vid": v.get("vid", ""),
            "topic": v.get("topic", ""),
            "status_display": status_display,
            "publish_date": v.get("publish_date") or "—",
            "views": _view_str(bf.get("views")) if bf else "—",
            "retention": str(bf.get("retention_3s", "—")) if bf and bf.get("retention_3s") is not None else "—",
            "completion": str(bf.get("completion_rate", "—")) if bf and bf.get("completion_rate") is not None else "—",
            "tier": tier,
            "post_type": _infer_post_type(bf) if bf and bf.get("views") else "—",
            "weaknesses": _weaknesses_str(bf) if bf and bf.get("views") else "—",
            "next_action": next_action,
            "_sort_group": sort_group,
            "_sort_days": days,
            "_raw_views": int(bf.get("views") or 0) if bf else 0,
        })

    # 初始排序：按群組分塊，待拍按天數降序
    enriched.sort(key=lambda x: (
        x["_sort_group"],
        -x["_sort_days"],
    ))
    # 已上線: 觀看數降序（最多觀看在前）
    online = [e for e in enriched if e["_sort_group"] == 0]
    online.sort(key=lambda x: x["_raw_views"], reverse=True)
    rest = [e for e in enriched if e["_sort_group"] > 0]
    enriched = online + rest

    # Stats
    counts = {"待拍": 0, "已上線": 0, "剪輯中": 0}
    total_ret = []
    total_comp = []
    for v in items:
        if not v.get("vid"):
            continue
        s = v.get("status", "")
        if s in counts:
            counts[s] += 1
        bf = v.get("backfill") or {}
        if bf.get("retention_3s") is not None:
            try:
                total_ret.append(float(bf["retention_3s"]))
            except (TypeError, ValueError):
                pass
        if bf.get("completion_rate") is not None:
            try:
                total_comp.append(float(bf["completion_rate"]))
            except (TypeError, ValueError):
                pass

    avg_ret = f"{sum(total_ret)/len(total_ret):.1f}%" if total_ret else "—"
    avg_comp = f"{sum(total_comp)/len(total_comp):.1f}%" if total_comp else "—"

    # Count each type of action needed
    action_counts = {}
    for e in enriched:
        a = e["next_action"]
        if a.startswith("📌"):
            action_counts["需補互動明細"] = action_counts.get("需補互動明細", 0) + 1
        elif a.startswith("📝"):
            action_counts["需寫腳本"] = action_counts.get("需寫腳本", 0) + 1
        elif a.startswith("⚠️"):
            action_counts["卡太久"] = action_counts.get("卡太久", 0) + 1
        elif a.startswith("📊"):
            action_counts["需回填數據"] = action_counts.get("需回填數據", 0) + 1

    action_parts = [f"{v}支{k}" for k, v in action_counts.items()] if action_counts else []

    rows = [
        [
            "📊 影片總覽",
            f"待拍:{counts['待拍']}",
            f"已上線:{counts['已上線']}",
            f"平均留存:{avg_ret}",
            f"平均完播:{avg_comp}",
        ] + action_parts + [""] * (11 - 5 - len(action_parts) - 1) + [
            f"更新：{now.strftime('%Y-%m-%d %H:%M')}"
        ],
        ["影片碼", "主題", "狀態", "上片日", "觀看數", "留存%",
         "完播%", "表現", "貼文類型", "弱點", "下一步"],
    ]

    if not enriched:
        rows.append(["（尚無影片）"] + [""] * 10)
    else:
        for e in enriched:
            rows.append([
                e["vid"], e["topic"], e["status_display"], e["publish_date"],
                e["views"], e["retention"], e["completion"], e["tier"],
                e["post_type"], e["weaknesses"], e["next_action"],
            ])

    return rows


# ── 待辦 ──────────────────────────────────────────────

def build_todo_rows(work_pending, misc_pending):
    """待辦分頁：智能看板（僅顯示未完成項目）"""
    now = now_tw()
    today = now.date()

    def _urgency(item):
        due_str = item.get("due_date", "")
        if not due_str:
            return "（無到期日）"
        try:
            due = datetime.strptime(due_str.lstrip("'"), "%Y-%m-%d").date()
            delta = (due - today).days
            if delta < 0:
                return f"🔴 逾期 {-delta} 天"
            elif delta == 0:
                return "🟡 今天到期"
            elif delta == 1:
                return "⚠️ 明天到期"
            elif delta <= 7:
                return f"📅 {delta} 天後"
            else:
                return ""
        except ValueError:
            return ""

    def _sort_key(item):
        due_str = item.get("due_date", "")
        if not due_str:
            return (2, 9999)
        try:
            due = datetime.strptime(due_str.lstrip("'"), "%Y-%m-%d").date()
            delta = (due - today).days
            return (0 if delta < 0 else 1, delta)
        except ValueError:
            return (2, 9999)

    def _count_overdue(items):
        n = 0
        for it in items:
            due_str = it.get("due_date", "")
            if due_str:
                try:
                    due = datetime.strptime(due_str.lstrip("'"), "%Y-%m-%d").date()
                    if (due - today).days < 0:
                        n += 1
                except ValueError:
                    pass
        return n

    all_pending = work_pending + misc_pending
    total_overdue = _count_overdue(all_pending)

    if total_overdue > 0:
        health = f"🔴 共有 {total_overdue} 條逾期待辦 → 優先處理！"
    elif not all_pending:
        health = "✅ 待辦清單全數清空！"
    else:
        health = "✅ 無逾期，按計劃進行"

    rows = [
        [f"待辦 {len(all_pending)} 項未完成（逾期 {total_overdue} 項）",
         "", "", f"更新：{now.strftime('%Y-%m-%d %H:%M')}"],
        [health, "", "", ""],
        [],
        ["項目", "到期日", "緊急旗標", "備註"],
    ]

    if all_pending:
        for item in sorted(all_pending, key=_sort_key):
            rows.append([item["task"], as_text_date(item.get("due_date", "")),
                         _urgency(item), ""])
    else:
        rows.append(["（空）", "", "", ""])

    return rows



# ── 報表 ──────────────────────────────────────────────

def build_report_rows(video_stats=None, inspiration_stats=None, done_stats=None,
                      weekly_data=None):
    """報表分頁：影片產量 + 靈感轉化 + 完成統計 + 表現指標。

    若傳入 weekly_data（weekly_report() 的回傳值），使用其豐富指標。
    否則回退到舊的 video_stats/inspiration_stats 模式（向下相容）。
    """
    now = now_tw()
    week_start = now - timedelta(days=now.weekday())
    week_str = f"{week_start.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"
    month_str = now.strftime("%Y 年 %m 月")

    vs = video_stats or {}

    rows = [
        ["📊 報表", "", f"更新：{now.strftime('%Y-%m-%d %H:%M')}"],
        [],
        ["━━ 本週影片產量 ━━", f"本週：{week_str}", ""],
        ["上線", str(vs.get("week_online", 0)), ""],
        ["剪輯中", str(vs.get("week_editing", 0)), ""],
        ["待拍", str(vs.get("week_shooting", 0)), ""],
        [],
        ["━━ 本月影片產量 ━━", f"月份：{month_str}", ""],
        ["上線", str(vs.get("month_online", 0)), ""],
        ["總在製", str(vs.get("month_in_progress", 0)), ""],
    ]

    # ── 表現指標（來自 weekly_data）──
    if weekly_data:
        pc = weekly_data.get("perf_counts", {})
        bf_total = pc.get("high", 0) + pc.get("normal", 0) + pc.get("low", 0)
        rows.append([])
        rows.append(["━━ 累計表現 ━━", "", ""])
        rows.append(["回填影片數", str(bf_total), f"🏆高 {pc.get('high', 0)} / ⚠️普通 {pc.get('normal', 0)} / 📉低 {pc.get('low', 0)}"])
        rows.append(["平均留存", f"{weekly_data.get('avg_retention', 0)}%", ""])
        rows.append(["平均完播", f"{weekly_data.get('avg_completion', 0)}%", ""])
        # 開場/CTA 統計
        oc = weekly_data.get("opening_counts", {})
        if oc:
            parts = [f"{k}({v}次)" for k, v in sorted(oc.items(), key=lambda x: -x[1])[:5]]
            rows.append(["最強開場", " ".join(parts), ""])
        cc = weekly_data.get("cta_counts", {})
        if cc:
            parts = [f"{k}({v}次)" for k, v in sorted(cc.items(), key=lambda x: -x[1])[:5]]
            rows.append(["最強CTA", " ".join(parts), ""])
        # 路線對比
        sp = weekly_data.get("source_perf", {})
        if len(sp) >= 2:
            rows.append([])
            rows.append(["━━ 路線對比 ━━", "留存%", "完播%"])
            for src_name in ("pipeline", "quick-shot"):
                if src_name in sp:
                    s = sp[src_name]
                    rows.append([f"{src_name}（{s['count']}支）",
                                 f"{s['avg_retention']}%",
                                 f"{s['avg_completion']}%（高表現{s['high_rate']}%）"])

    if inspiration_stats:
        rows.append([])
        rows.append(["━━ 靈感轉化 ━━", "", ""])
        rows.append(["總靈感數", str(inspiration_stats["total"]), ""])
        rows.append(["📥 inbox", str(inspiration_stats["inbox"]), ""])
        rows.append(["❄️ cooldown", str(inspiration_stats["cooldown"]), ""])
        rows.append(["🎯 selected", str(inspiration_stats["selected"]), ""])
        if inspiration_stats["total"] > 0:
            conv = int(inspiration_stats["selected"] / inspiration_stats["total"] * 100)
            rows.append(["轉化率（selected/total）", f"{conv}%", ""])

    ds = done_stats or {}
    if ds:
        rows.append([])
        rows.append(["━━ 待辦完成統計 ━━", "", ""])
        rows.append(["本月完成", str(ds.get("month_total", 0)), f"工作 {ds.get('month_work', 0)} + 雜事 {ds.get('month_misc', 0)}"])
        rows.append(["本週完成", str(ds.get("week_done", 0)), ""])

    return rows
