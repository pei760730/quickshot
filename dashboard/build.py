#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard build — 讀 data/kai/*.json → 依 ui-contract 填進 index.html。

用法：
  python3 dashboard/build.py            # build 到 dashboard/dist/index.html
  python3 dashboard/build.py --dry-run  # 只印 schema 產出、不寫檔

SSoT：dashboard/src/data-schema.json + dashboard/src/ui-contract.md
產出：dashboard/dist/index.html（Vercel deploy target）
"""

from __future__ import annotations
import json
import sys
import subprocess
import re
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "dashboard" / "src"
DIST = REPO / "dashboard" / "dist"
OPERATOR = "kai"


# ── 資料聚合 ────────────────────────────────────────────

def _pct(n: float) -> str:
    return f"{n:.1f}%"


def _short_num(n: int) -> str:
    """格式化大數字（對齊 Sheets 影片總覽的「萬」制）。

    規則（與 scripts/utils/lib/builders.py:_view_str 對齊）：
    - v >= 1 億       → `X.X億`
    - v >= 1 萬       → `X.X萬`
    - 其他           → 原始數字字串
    """
    try:
        v = int(n)
    except (TypeError, ValueError):
        return "—"
    if v >= 100_000_000:
        return f"{v/100_000_000:.1f}億"
    if v >= 10_000:
        return f"{v/10_000:.1f}萬"
    return str(v)


def _k_num(n) -> str:
    """社群粉絲專用：k / M 格式、小數 2 位、向下截斷不進位（Kai 要求）。
    2,488 → 2.48k、1,986 → 1.98k、1,900 → 1.90k。"""
    try:
        v = int(n)
    except (TypeError, ValueError):
        return "—"
    if v >= 1_000_000:
        truncated = int(v / 10_000) / 100  # 保留 2 位不進位
        return f"{truncated:.2f}M"
    if v >= 1_000:
        truncated = int(v / 10) / 100
        return f"{truncated:.2f}k"
    return str(v)


def _short_bytes(size: int) -> str:
    """檔案大小（非觀看數）的短格式。分開 _short_num 避免混淆。"""
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{size/1024:.1f}K"
    return f"{size/(1024*1024):.1f}M"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True
        ).strip()
    except Exception:
        return "unknown"


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _file_info(rel: str):
    p = REPO / rel
    if not p.exists():
        return {"path": rel, "size_readable": "missing", "exists": False}
    size = p.stat().st_size
    return {
        "path": rel,
        "size_readable": _short_bytes(size),
        "exists": True,
    }


def _days_since(date_str: str, today: datetime.date) -> int:
    if not date_str:
        return 0
    try:
        d = datetime.date.fromisoformat(str(date_str)[:10])
    except Exception:
        return 0
    return max(0, (today - d).days)


def _engine_version() -> str:
    m = _load(REPO / "engine-manifest.json", {"_meta": {}})
    return m.get("_meta", {}).get("engine_version", "?")


def _social_platforms(today: datetime.date) -> list[dict]:
    """讀 social-followers.json、為每個平台算最新 + 增長 + 距今天數。"""
    data = _load(REPO / f"data/{OPERATOR}/social-followers.json", {"platforms": {}})
    out = []
    for key, p in (data.get("platforms") or {}).items():
        history = p.get("history") or []
        latest = history[-1] if history else None
        prev = history[-2] if len(history) >= 2 else None
        if latest is None:
            followers_display = "—"
            growth_display = "待補圖"
            updated_display = "—"
        else:
            followers = int(latest.get("followers") or 0)
            # 社群粉絲：全部用 k/M 格式（2,488 → 2.5k、1.2M 為上限前）
            followers_display = _k_num(followers)
            # 顯示實際日期（MM-DD）、不用「今天 / N 天前」相對詞
            updated_display = str(latest.get("date", ""))[5:10] or "—"
            if prev is not None:
                diff = followers - int(prev.get("followers") or 0)
                sign = "↑" if diff > 0 else ("↓" if diff < 0 else "·")
                growth_display = f"{sign} {_k_num(abs(diff))}" if diff != 0 else "持平"
            else:
                growth_display = "首次記錄"
        out.append({
            "key": key,
            "display_name": p.get("display_name", key),
            "icon": p.get("icon", "•"),
            "handle": p.get("handle", ""),
            "profile_url": p.get("profile_url", "#"),
            "followers_display": followers_display,
            "growth_display": growth_display,
            "updated_display": updated_display,
        })
    return out


def aggregate(today: datetime.date) -> dict:
    pipeline = _load(REPO / f"data/{OPERATOR}/pipeline.json", {"_meta": {}, "items": []})
    meta = pipeline.get("_meta", {})
    items = pipeline.get("items", [])
    thresholds = meta.get("thresholds", {})
    perf = thresholds.get("performance", {})
    stale = thresholds.get("stale_days", {})
    social = _social_platforms(today)

    # 分類
    online = [it for it in items if it.get("status") == "已上線"]
    backfilled = [it for it in online if it.get("backfill")]
    videos_with_vid = [it for it in items if it.get("vid")]

    # 狀態計數
    status_counts = {"inbox": 0, "selected": 0, "待拍": 0, "剪輯中": 0, "已上線": 0}
    for it in items:
        s = it.get("status")
        if s in status_counts:
            status_counts[s] += 1

    ideas_total = status_counts["inbox"] + status_counts["selected"]

    # KPI 計算
    total_views = sum(int((it.get("backfill") or {}).get("views") or 0) for it in backfilled)
    views_list = [int((it.get("backfill") or {}).get("views") or 0) for it in backfilled]
    max_views = max(views_list) if views_list else 0

    retention_values = [
        float((it.get("backfill") or {}).get("retention_3s") or 0)
        for it in backfilled
        if (it.get("backfill") or {}).get("retention_3s") is not None
    ]
    completion_values = [
        float((it.get("backfill") or {}).get("completion_rate") or 0)
        for it in backfilled
        if (it.get("backfill") or {}).get("completion_rate") is not None
    ]
    avg_retention = sum(retention_values) / len(retention_values) if retention_values else 0
    avg_completion = sum(completion_values) / len(completion_values) if completion_values else 0

    high = [it for it in backfilled if (it.get("backfill") or {}).get("performance") == "high"]
    normal = [it for it in backfilled if (it.get("backfill") or {}).get("performance") == "normal"]
    low = [it for it in backfilled if (it.get("backfill") or {}).get("performance") == "low"]

    sample_size = len(backfilled)
    win_rate = (len(high) / sample_size * 100) if sample_size else 0

    # v1.7 KPI 子資訊：達標計數 + 最新爆款
    retention_pass_count = sum(1 for r in retention_values if r >= 55)
    completion_pass_count = sum(1 for c in completion_values if c >= 40)
    avg_views_per_video = total_views // sample_size if sample_size else 0
    # 最新高表現：high 中 publish_date 最新者
    latest_high = max(
        high,
        key=lambda it: str(it.get("publish_date") or ""),
        default=None,
    )
    latest_high_vid = latest_high.get("vid", "—") if latest_high else "—"
    latest_high_title = (
        (latest_high.get("title") or latest_high.get("topic") or "—")
        if latest_high else "—"
    )

    kpis = {
        "accumulated_views": total_views,
        "accumulated_views_display": _short_num(total_views),
        "avg_views_per_video_display": _short_num(avg_views_per_video),
        "max_views_display": _short_num(max_views),
        "sample_size": sample_size,
        "total_uploaded": len(online),
        "avg_retention_3s_pct": round(avg_retention, 1),
        "avg_retention_3s_pct_display": _pct(avg_retention),
        "retention_pass_count": retention_pass_count,
        "avg_completion_rate_pct": round(avg_completion, 1),
        "avg_completion_rate_pct_display": _pct(avg_completion),
        "completion_pass_count": completion_pass_count,
        "high_performers_count": len(high),
        "win_rate_pct": round(win_rate, 1),
        "win_rate_pct_display": f"{win_rate:.0f}%",
        "latest_high_vid": latest_high_vid,
        "latest_high_title": latest_high_title,
        "thresholds": {
            "retention_pass": 55,  # 導出：高表現門檻 70、正常 55 為慣例
            "retention_high": int(perf.get("high_A", {}).get("retention_3s", 70)),
            "completion_pass": int(perf.get("high_A", {}).get("completion_rate", 40)),
        },
    }

    nav_counts = {
        **status_counts,
        "total_videos": len(videos_with_vid),
        "total_ideas": ideas_total,
        "performance_high": len(high),
        "performance_normal": len(normal),
        "performance_low": len(low),
    }

    # Top 5 高/低表現：雙邊對稱、皆 performance 標籤先過濾 + views 降冪
    # 容量上限 5、若實際不足 5（如 low=4）直接顯示該數量、不補位
    def _row(it):
        bf = it.get("backfill") or {}
        return {
            "vid": it.get("vid", "—"),
            "title": it.get("title") or it.get("topic") or "—",
            "views_display": _short_num(int(bf.get("views") or 0)),
            "retention_3s_pct_display": _pct(float(bf.get("retention_3s") or 0)),
            "completion_rate_pct_display": _pct(float(bf.get("completion_rate") or 0)),
        }

    def _by_views_desc(pool):
        return sorted(
            pool,
            key=lambda it: int((it.get("backfill") or {}).get("views") or 0),
            reverse=True,
        )

    top5_list = [_row(it) for it in _by_views_desc(high)[:5]]
    top5_low_list = [_row(it) for it in _by_views_desc(low)[:5]]

    # 卡關偵測
    stuck_by_status = []
    stuck_counts = {}
    stuck_thresholds = {}
    status_display = {"inbox": "靈感 INBOX", "selected": "靈感 SELECTED", "待拍": "待拍", "剪輯中": "剪輯中"}
    for status_key in ["inbox", "selected", "待拍", "剪輯中"]:
        threshold_days = stale.get(status_key, 7)
        in_status = [it for it in items if it.get("status") == status_key]
        oldest = 0
        stuck_count = 0
        for it in in_status:
            d = _days_since(it.get("created_date", ""), today)
            if d > oldest:
                oldest = d
            if d > threshold_days:
                stuck_count += 1
        stuck_by_status.append({
            "status": status_key,
            "status_display": status_display.get(status_key, status_key),
            "count": stuck_count,
            "stale_days_threshold": threshold_days,
            "oldest_days": oldest,
            "count_severity": "alert" if stuck_count > 0 else "ok",
        })
        stuck_counts[status_key] = stuck_count
        stuck_thresholds[status_key] = threshold_days

    data_files = [
        _file_info(f"data/{OPERATOR}/pipeline.json"),
        _file_info(f"data/{OPERATOR}/performance-patterns.json"),
        _file_info(f"data/{OPERATOR}/brand-monitor.json"),
    ]

    # ── v1.1 lists（tab 內容）─────────────────────────
    idea_status_display = {"inbox": "收集中", "selected": "已選定", "cooldown": "冷凍中"}

    # v1.3: tier display 對齊 Sheets 影片總覽的 classify_performance_display
    # 讀 pipeline _meta.thresholds.performance（不 hardcode），對齊 SSoT
    def _tier_display(bf):
        if not bf or bf.get("views") is None:
            return "—"
        try:
            v = float(bf.get("views") or 0)
            r = float(bf.get("retention_3s") or 0)
            c = float(bf.get("completion_rate") or 0)
        except (TypeError, ValueError):
            return "—"
        if v == 0 and r == 0:
            return "—"
        high_a_cfg = perf.get("high_A", {})
        high_b_cfg = perf.get("high_B", {})
        low_cfg = perf.get("low", {})
        high_a = r >= float(high_a_cfg.get("retention_3s", 70)) and c >= float(high_a_cfg.get("completion_rate", 40))
        high_b = v >= float(high_b_cfg.get("views", 300000)) and c >= float(high_b_cfg.get("completion_rate", 40))
        is_low = (r < float(low_cfg.get("retention_3s_below", 40))
                  or c < float(low_cfg.get("completion_rate_below", 15)))
        if high_a and high_b:
            return "🟢 高+觸及"
        if high_a:
            return "🟡 高留存"
        if high_b:
            return "🟠 高觸及"
        if is_low:
            return "🔴 低"
        return "· 普通"

    # v1.3: next_action 對齊 Sheets builders.py 的 _next_action
    def _next_action(it):
        status = it.get("status", "")
        if status == "待拍":
            has_script = bool(it.get("script_path"))
            d = _days_since(it.get("created_date", ""), today)
            if not has_script:
                return "📝 需寫腳本"
            if d > 30:
                return "⚠️ 卡太久"
            if d > 7:
                return f"⏰ 等 {d}天"
            return "✅ 可拍"
        if status == "剪輯中":
            return "✂️ 剪輯中"
        if status == "已上線":
            bf = it.get("backfill")
            if not bf:
                return "📊 需回填"
            missing = [f for f in ["likes", "comments", "shares", "saves"] if bf.get(f) is None]
            if missing:
                return "📌 補 " + "/".join(missing[:2])
            return "✅ 完成"
        return status or "—"

    def _tags_str(it):
        t = it.get("tags") or []
        if isinstance(t, str):
            return t
        return " ".join(f"#{x}" for x in t[:3])

    # backlog（待拍）
    backlog_items = [it for it in items if it.get("status") == "待拍"]
    backlog_items.sort(key=lambda it: it.get("created_date", ""), reverse=True)
    backlog_list = [
        {
            "vid": it.get("vid", ""),
            "title": it.get("title") or it.get("topic") or "—",
            "tags_display": _tags_str(it),
            "days_waiting": _days_since(it.get("created_date", ""), today),
            "days_waiting_display": f"{_days_since(it.get('created_date', ''), today)} 天",
            "hook_reason": it.get("hook_reason") or "—",
        }
        for it in backlog_items
    ]

    # online（已上線全部，依觀看數 desc 對齊 Sheets 影片總覽）
    online_items_sorted = sorted(
        online,
        key=lambda it: int((it.get("backfill") or {}).get("views") or 0),
        reverse=True,
    )
    def _online_row(it):
        bf = it.get("backfill") or {}
        views = int(bf.get("views") or 0)
        retention = float(bf.get("retention_3s") or 0)
        completion = float(bf.get("completion_rate") or 0)
        perf_val = bf.get("performance")
        return {
            "vid": it.get("vid", ""),
            "title": it.get("title") or it.get("topic") or "—",
            "publish_date": (it.get("publish_date") or "—")[:10],
            "views": views,
            "views_display": _short_num(views) if views else "—",
            "retention_3s_pct": round(retention, 1),
            "retention_3s_pct_display": _pct(retention) if retention else "—",
            "completion_rate_pct": round(completion, 1),
            "completion_rate_pct_display": _pct(completion) if completion else "—",
            "performance": perf_val or "unknown",
            "tier_display": _tier_display(bf),  # v1.3: 對齊 Sheets
            "next_action": _next_action(it),    # v1.3: 對齊 Sheets
        }
    online_list = [_online_row(it) for it in online_items_sorted]

    # high_performers_full（全部高表現，依 views desc）
    high_sorted = sorted(
        high,
        key=lambda it: int((it.get("backfill") or {}).get("views") or 0),
        reverse=True,
    )
    high_full_list = [_online_row(it) for it in high_sorted]

    # normal_performers_full（v1.4 新增，依 views desc）
    normal_sorted = sorted(
        normal,
        key=lambda it: int((it.get("backfill") or {}).get("views") or 0),
        reverse=True,
    )
    normal_full_list = [_online_row(it) for it in normal_sorted]

    # low_performers_full（v1.4 新增，依 views desc）
    low_sorted = sorted(
        low,
        key=lambda it: int((it.get("backfill") or {}).get("views") or 0),
        reverse=True,
    )
    low_full_list = [_online_row(it) for it in low_sorted]

    # ideas（inbox + selected，依 created_date 新到舊）
    idea_items = [it for it in items if it.get("status") in ("inbox", "selected")]
    idea_items.sort(key=lambda it: it.get("created_date", ""), reverse=True)
    ideas_list = [
        {
            "idea_id": it.get("idea_id", ""),
            "topic": it.get("topic") or it.get("title") or "—",
            "status": it.get("status"),
            "status_display": idea_status_display.get(it.get("status"), it.get("status", "")),
            "days_old": _days_since(it.get("created_date", ""), today),
            "days_old_display": f"{_days_since(it.get('created_date', ''), today)} 天",
            "tags_display": _tags_str(it),
            "hook_reason": it.get("hook_reason") or "—",
        }
        for it in idea_items
    ]

    return {
        "meta": {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "operator": OPERATOR,
            "engine_version": f"v{_engine_version()}",
            "source_commit": _git_sha(),
        },
        "social_platforms": social,
        "kpis": kpis,
        "nav_counts": nav_counts,
        "top5_high_performers": top5_list,
        "top5_low_performers": top5_low_list,
        "stuck_by_status": stuck_by_status,
        "stuck_counts": stuck_counts,
        "stuck_thresholds": stuck_thresholds,
        "data_files": data_files,
        "lists": {
            "backlog": backlog_list,
            "online": online_list,
            "high_performers_full": high_full_list,
            "normal_performers_full": normal_full_list,
            "low_performers_full": low_full_list,
            "ideas": ideas_list,
        },
    }


# ── HTML inject（簡易 DOM 取代）────────────────────────

def _get(data, path: str):
    """v1.11: 支援 list 數字索引（social_platforms.0.icon）。"""
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if cur is None:
            return None
    return cur


def _replace_field(item_template: str, field: str, value: str) -> str:
    """把 item template 裡 <TAG ... data-bind-field="field">...</TAG> 的 innerText 換成 value。
    用反向引用處理 tag 配對，內層含嵌套 span 也能正確抓到 close tag（前提：item template 本身沒有同 TAG 嵌套）。"""
    pattern = re.compile(
        r'(<([a-zA-Z][a-zA-Z0-9]*)[^>]*data-bind-field="' + re.escape(field) + r'"[^>]*>)(.*?)(</\2>)',
        re.DOTALL,
    )
    return pattern.sub(lambda m: m.group(1) + str(value) + m.group(4), item_template)


def _extract_item_template(container_inner: str) -> tuple[str, str, str]:
    """從 container 內容找第一個 <TAG ... data-bind-item ...>...</TAG>。
    回傳 (before, template, after)，template 含開/關 tag。
    用反向引用避免嵌套誤判。"""
    m = re.search(
        r'(<([a-zA-Z][a-zA-Z0-9]*)[^>]*data-bind-item[^>]*>.*?</\2>)',
        container_inner,
        re.DOTALL,
    )
    if not m:
        return container_inner, "", ""
    return container_inner[:m.start()], m.group(1), container_inner[m.end():]


def inject(html: str, data: dict) -> str:
    # 1. 處理 data-bind-list（先，避免內部 data-bind-field 被下階段錯替）
    list_pattern = re.compile(
        r'(<([a-zA-Z][a-zA-Z0-9]*)[^>]*data-bind-list="([^"]+)"[^>]*>)(.*?)(</\2>)',
        re.DOTALL,
    )

    def _list_repl(m):
        open_tag = m.group(1)
        path = m.group(3)
        inner = m.group(4)
        close_tag = m.group(5)
        items = _get(data, path) or []
        before, template, after = _extract_item_template(inner)
        if not template:
            return open_tag + inner + close_tag
        rendered = []
        for item in items:
            t = template
            if isinstance(item, dict):
                for k, v in item.items():
                    t = _replace_field(t, k, v)
            rendered.append(t)
        return open_tag + before + "\n".join(rendered) + after + close_tag

    html = list_pattern.sub(_list_repl, html)

    # 2. 處理 data-bind（非 list/field）
    simple_pattern = re.compile(
        r'(<([a-zA-Z][a-zA-Z0-9]*)[^>]*data-bind="([^"]+)"[^>]*>)([^<]*)(</\2>)'
    )

    def _simple_repl(m):
        open_tag = m.group(1)
        path = m.group(3)
        close_tag = m.group(5)
        value = _get(data, path)
        if value is None:
            value = "—"
        return open_tag + str(value) + close_tag

    html = simple_pattern.sub(_simple_repl, html)

    # 3. data-bind-href：<a ... data-bind-href="path"> 替換 href 屬性
    #    支援整卡可點擊（social cards）
    href_tag_pattern = re.compile(r'<a\s[^>]*data-bind-href="[^"]+"[^>]*>', re.DOTALL)

    def _href_tag_repl(m):
        tag_html = m.group(0)
        path_m = re.search(r'data-bind-href="([^"]+)"', tag_html)
        if not path_m:
            return tag_html
        value = _get(data, path_m.group(1)) or "#"
        # 檢查是否有獨立 href=（排除 data-bind-href 的子字串）
        if re.search(r'(?:^|\s)href="', tag_html):
            tag_html = re.sub(r'(?:^|\s)href="[^"]*"', f' href="{value}"', tag_html, count=1)
        else:
            tag_html = tag_html.replace("<a ", f'<a href="{value}" ', 1)
        return tag_html

    html = href_tag_pattern.sub(_href_tag_repl, html)

    return html


# ── Main ─────────────────────────────────────────────

def main():
    dry = "--dry-run" in sys.argv
    today = datetime.date.today()
    data = aggregate(today)

    if dry:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return

    src_html = (SRC / "index.html").read_text(encoding="utf-8")
    out_html = inject(src_html, data)

    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(out_html, encoding="utf-8")
    # 附帶輸出資料 snapshot（debug 用）
    (DIST / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    kb = (DIST / "index.html").stat().st_size / 1024
    print(f"✅ dashboard/dist/index.html ({kb:.1f} KB) + data.json")
    print(f"   sample={data['kpis']['sample_size']}/{data['kpis']['total_uploaded']} "
          f"· retention={data['kpis']['avg_retention_3s_pct_display']} "
          f"· high={data['kpis']['high_performers_count']} "
          f"· win_rate={data['kpis']['win_rate_pct_display']}")


if __name__ == "__main__":
    main()
