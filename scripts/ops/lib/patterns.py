#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance patterns：CRUD + 衰減 + 清理。

所有 proven_openings / proven_ctas / proven_formulas 的遍歷
都透過 PATTERN_KEYS 驅動，確保新增類型時只改一處。
"""

from . import config as _cfg
from .config import PATTERN_THRESHOLDS, today_str
from .storage import load_json, save_json


# ── 統一定義 ─────────────────────────────────────────────

# 所有 pattern 類型與其 id 欄位名稱。
# 新增第四類 pattern 只需在此新增一行。
PATTERN_KEYS = {
    "proven_openings": "code",
    "proven_ctas":     "code",
    "proven_formulas": "formula",
}


def win_rate_note(item):
    """計算 win_rate_note（即時算，不再存 JSON）。

    若 item 含 win_rate 和 confidence（由 compute_pattern_stats 計算），
    會顯示更豐富的資訊。
    """
    count = len(item.get("vid_evidence", []))
    confidence = item.get("confidence")
    win_rate = item.get("win_rate")
    if win_rate is not None and confidence:
        return f"{count} 次高表現（勝率 {win_rate:.0%}，信心 {confidence}）"
    return f"{count} 次高表現使用"


def _confidence_level(total_uses):
    """根據 total_uses 回傳 low/medium/high 信心等級。"""
    th = PATTERN_THRESHOLDS
    if total_uses >= th["confidence_high_min"]:
        return "high"
    if total_uses >= th["confidence_medium_min"]:
        return "medium"
    return "low"


# ── IO ───────────────────────────────────────────────────

def load_performance_patterns(performance_patterns_json=None):
    """讀取 performance-patterns.json"""
    path = performance_patterns_json or _cfg.PERFORMANCE_PATTERNS_JSON
    return load_json(
        path,
        {"_meta": {"last_updated": today_str()}, "proven_openings": [],
         "proven_ctas": [], "proven_formulas": [], "risk_patterns": []},
        "performance-patterns.json",
    )


def save_performance_patterns(pdata, performance_patterns_json=None):
    """寫入 performance-patterns.json"""
    path = performance_patterns_json or _cfg.PERFORMANCE_PATTERNS_JSON
    save_json(path, pdata)


# ── 衰減 ─────────────────────────────────────────────────

def _check_pattern_decay(pdata, opening=None, cta=None, formula=None, vid=None):
    """低表現影片使用 proven pattern 時，記錄 low_evidence。

    累計 low_evidence >= PATTERN_THRESHOLDS["decay_low_evidence_trigger"]
    → 標記 degraded=True，generation skill 會讀取此旗標並降級處理。
    """
    decay_trigger = PATTERN_THRESHOLDS["decay_low_evidence_trigger"]
    changed = False
    lookup = {"proven_openings": opening, "proven_ctas": cta, "proven_formulas": formula}
    for key, id_field in PATTERN_KEYS.items():
        target = lookup.get(key)
        if not target:
            continue
        for item in pdata.get(key, []):
            if item.get(id_field) != target:
                continue
            low_ev = item.setdefault("low_evidence", [])
            if vid and vid not in low_ev:
                low_ev.append(vid)
                changed = True
            if len(low_ev) >= decay_trigger and not item.get("degraded"):
                item["degraded"] = True
                item["degraded_date"] = today_str()
                item["degraded_reason"] = (
                    f"{len(low_ev)} 支低表現影片使用此 pattern"
                    f"（{', '.join(low_ev[:5])}）"
                )
                changed = True
            break
    return changed


def _add_vid_evidence(pdata, key, code, vid):
    """在 proven_openings / proven_ctas / proven_formulas 中為指定 code 追加 VID 證據。

    自動處理舊格式遷移（orphan "vid" 欄位 → vid_evidence 陣列）。
    新增 proven_formulas 時會帶 tags + added_date。
    """
    id_field = PATTERN_KEYS[key]
    items = pdata.get(key, [])
    for item in items:
        if item.get(id_field) == code:
            # 舊格式遷移：清理 orphan vid 欄位 → vid_evidence
            if "vid" in item:
                old_vid = item.pop("vid")
                if old_vid and old_vid not in item.get("vid_evidence", []):
                    item.setdefault("vid_evidence", []).append(old_vid)
            if "vid_evidence" not in item:
                item["vid_evidence"] = []
            if vid not in item["vid_evidence"]:
                item["vid_evidence"].append(vid)
            item["last_evidence_date"] = today_str()
            return
    new_item = {id_field: code, "vid_evidence": [vid], "last_evidence_date": today_str()}
    if id_field == "code":
        new_item["name"] = code
    else:
        # proven_formulas 新增時帶 tags + added_date
        new_item["tags"] = []
        new_item["added_date"] = today_str()
    items.append(new_item)
    pdata[key] = items


def _remove_vid_from_patterns(vid, old_learning):
    """re-backfill 降級時，從 performance-patterns 移除該 VID 的證據。"""
    pdata = load_performance_patterns()
    changed = False
    lookup = {
        "proven_openings": old_learning.get("opening"),
        "proven_ctas": old_learning.get("cta"),
        "proven_formulas": old_learning.get("formula"),
    }
    for key, id_field in PATTERN_KEYS.items():
        target = lookup.get(key)
        if not target:
            continue
        for item in pdata.get(key, []):
            if item.get(id_field) == target:
                ev = item.get("vid_evidence", [])
                if vid in ev:
                    ev.remove(vid)
                    changed = True
                break

    if changed:
        save_performance_patterns(pdata)


def _remove_vid_from_low_evidence(vid):
    """re-backfill 升級（low→non-low）時，從 low_evidence 移除該 VID。

    若移除後 low_evidence 數量低於 decay 門檻，撤銷 degraded 標記。
    同時移除 risk_patterns 中該 VID 的記錄。
    """
    pdata = load_performance_patterns()
    decay_trigger = PATTERN_THRESHOLDS["decay_low_evidence_trigger"]
    changed = False

    for key in PATTERN_KEYS:
        for item in pdata.get(key, []):
            low_ev = item.get("low_evidence", [])
            if vid in low_ev:
                low_ev.remove(vid)
                changed = True
                if item.get("degraded") and len(low_ev) < decay_trigger:
                    item["degraded"] = False
                    item.pop("degraded_date", None)
                    item["degraded_reason"] = (
                        f"撤銷：{vid} 升級後 low_evidence 降至"
                        f" {len(low_ev)}<{decay_trigger}"
                    )

    # 清除 risk_patterns 中該 VID 的記錄
    old_risks = pdata.get("risk_patterns", [])
    new_risks = [r for r in old_risks if r.get("vid") != vid]
    if len(new_risks) != len(old_risks):
        pdata["risk_patterns"] = new_risks
        changed = True

    if changed:
        save_performance_patterns(pdata)
    return changed


# ── 清理 ─────────────────────────────────────────────────

def cleanup_unverified_formulas(pdata, threshold_days=30):
    """將建立超過 threshold_days 天且 vid_evidence 為空的公式移到 unverified_formulas。

    回傳 moved 清單。
    """
    from datetime import datetime
    from .config import TW_TZ, today_str

    today = today_str()
    try:
        now = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=TW_TZ)
    except ValueError:
        now = datetime.now(TW_TZ)
    proven = pdata.get("proven_formulas", [])
    keep = []
    moved = []

    for f in proven:
        evidence = f.get("vid_evidence", [])
        if not evidence:
            # 檢查是否有 added_date；沒有表示建立時間不明（早期手動加入），視為已過期
            added = f.get("added_date")
            if not added:
                added = "2020-01-01"  # 無追蹤日期，視為早期資料（必定超過門檻）
            try:
                added_dt = datetime.strptime(added, "%Y-%m-%d").replace(tzinfo=TW_TZ)
            except ValueError:
                added_dt = datetime.strptime("2020-01-01", "%Y-%m-%d").replace(tzinfo=TW_TZ)
            days = (now - added_dt).days
            if days >= threshold_days:
                moved.append(f)
                continue
        keep.append(f)

    if moved:
        pdata["proven_formulas"] = keep
        unverified = pdata.setdefault("unverified_formulas", [])
        for f in moved:
            f["moved_date"] = today
            f["moved_reason"] = f"建立超過 {threshold_days} 天，零 VID 證據"
            unverified.append(f)

    return moved


# ── 統計計算 ─────────────────────────────────────────────

def compute_pattern_stats(pdata, pipeline_items):
    """從 pipeline 影片資料計算每個 proven pattern 的統計指標。

    為每個 pattern 寫入：
    - sample_size: 高表現證據數
    - total_uses: 所有使用此 pattern 的已回填影片數（含高/普/低）
    - win_rate: sample_size / total_uses
    - confidence: low / medium / high

    pipeline_items: pipeline.json 的 items 陣列。
    回傳被更新的 pattern 數量。
    """
    # 建立已回填影片索引
    vid_info = {}
    for item in pipeline_items:
        vid = item.get("vid")
        if not vid:
            continue
        bf = item.get("backfill") or {}
        if not bf.get("backfilled_date") and not bf.get("views"):
            continue
        learning = item.get("learning") or {}
        vid_info[vid] = {
            "performance": bf.get("performance", "normal"),
            "hook_type": item.get("hook_type"),
            "tags": item.get("tags", ""),
            "version": item.get("version"),
            "title_type": item.get("title_type"),
            "learning_opening": learning.get("opening"),
            "learning_cta": learning.get("cta"),
            "learning_formula": learning.get("formula"),
        }

    updated = 0

    # 每種 pattern 類型分別統計
    for key, id_field in PATTERN_KEYS.items():
        for item in pdata.get(key, []):
            code = item.get(id_field)
            evidence = item.get("vid_evidence", [])
            high_count = len(evidence)

            # 統計 total_uses：所有已回填影片中使用此 pattern 的數量
            total_uses = 0
            if key == "proven_openings":
                # 開場類型：從 hook_type 或 learning.opening 匹配
                for vi in vid_info.values():
                    if vi.get("hook_type") == code or vi.get("learning_opening") == code:
                        total_uses += 1
            elif key == "proven_ctas":
                # CTA 類型：從 learning.cta 匹配
                for vi in vid_info.values():
                    if vi.get("learning_cta") == code:
                        total_uses += 1
            else:
                # formulas：無法自動匹配，用 evidence 數當底
                total_uses = high_count

            # high_count 永遠是 total_uses 的下限
            total_uses = max(total_uses, high_count)

            item["sample_size"] = high_count
            item["total_uses"] = total_uses
            item["win_rate"] = round(high_count / total_uses, 2) if total_uses > 0 else 0
            item["confidence"] = _confidence_level(total_uses)
            updated += 1

    return updated


def cross_dimensional_stats(pipeline_items):
    """從 pipeline 已回填影片計算多維度交叉分析。

    回傳 dict:
    - by_hook_type: {code: {count, high, normal, low, avg_retention, avg_completion}}
    - by_version: {version: {count, high, normal, low, avg_retention, avg_completion}}
    - by_topic_type: {tag: {count, high, normal, low, avg_retention, avg_completion}}
    - by_skill: {skill: {count, high, normal, low, avg_retention, avg_completion}}
    - combinations: [{hook_type, version, count, avg_retention, avg_completion, win_rate}]
      (只列 count >= 2 的組合)
    """
    by_hook = {}
    by_version = {}
    by_topic = {}
    by_skill = {}
    combo_map = {}  # (hook_type, version) -> stats

    for item in pipeline_items:
        vid = item.get("vid")
        if not vid:
            continue
        bf = item.get("backfill") or {}
        if not bf.get("backfilled_date") and not bf.get("views"):
            continue

        perf = bf.get("performance", "normal")
        ret = bf.get("retention_3s", 0)
        comp = bf.get("completion_rate", 0)

        hook = item.get("hook_type")
        version = item.get("version")
        tags = item.get("tags", "")
        skill = item.get("skill_used", "")

        for dim_map, dim_key in [(by_hook, hook), (by_version, version),
                                  (by_topic, tags), (by_skill, skill)]:
            if not dim_key:
                continue
            bucket = dim_map.setdefault(dim_key, {
                "count": 0, "high": 0, "normal": 0, "low": 0,
                "_ret_sum": 0, "_comp_sum": 0,
            })
            bucket["count"] += 1
            bucket[perf] = bucket.get(perf, 0) + 1
            bucket["_ret_sum"] += ret
            bucket["_comp_sum"] += comp

        # 組合：hook × version
        if hook and version:
            ck = (hook, version)
            cb = combo_map.setdefault(ck, {
                "hook_type": hook, "version": version,
                "count": 0, "high": 0, "_ret_sum": 0, "_comp_sum": 0,
            })
            cb["count"] += 1
            if perf == "high":
                cb["high"] += 1
            cb["_ret_sum"] += ret
            cb["_comp_sum"] += comp

    # 計算平均值
    for dim_map in [by_hook, by_version, by_topic, by_skill]:
        for bucket in dim_map.values():
            n = bucket["count"]
            bucket["avg_retention"] = round(bucket.pop("_ret_sum") / n, 1) if n else 0
            bucket["avg_completion"] = round(bucket.pop("_comp_sum") / n, 1) if n else 0

    # 組合：只保留 count >= 2
    combos = []
    for cb in combo_map.values():
        n = cb["count"]
        if n < 2:
            continue
        cb["avg_retention"] = round(cb.pop("_ret_sum") / n, 1)
        cb["avg_completion"] = round(cb.pop("_comp_sum") / n, 1)
        cb["win_rate"] = round(cb["high"] / n, 2) if n else 0
        combos.append(cb)

    combos.sort(key=lambda x: x["win_rate"], reverse=True)

    return {
        "by_hook_type": by_hook,
        "by_version": by_version,
        "by_topic_type": by_topic,
        "by_skill": by_skill,
        "combinations": combos,
    }


def skill_effectiveness(pipeline_items):
    """計算各 Skill 的生產效能。

    回傳 list[dict]，每個 dict:
    - skill: str
    - total: int — 總已回填影片數
    - high / normal / low: int — 各表現等級數量
    - win_rate: float — 高表現佔比
    - avg_retention: float
    - avg_completion: float
    - versions_used: dict[str, int] — 此 Skill 產出的版本分佈
    - avg_verifier_accuracy: float | None — verifier 預測準確率
    """
    skill_map = {}

    for item in pipeline_items:
        vid = item.get("vid")
        if not vid:
            continue
        bf = item.get("backfill") or {}
        if not bf.get("backfilled_date") and not bf.get("views"):
            continue

        skill = item.get("skill_used", "")
        if not skill:
            continue

        perf = bf.get("performance", "normal")
        ret = bf.get("retention_3s", 0)
        comp = bf.get("completion_rate", 0)
        version = item.get("version")
        va = item.get("verifier_accuracy")

        bucket = skill_map.setdefault(skill, {
            "skill": skill, "total": 0, "high": 0, "normal": 0, "low": 0,
            "_ret_sum": 0, "_comp_sum": 0, "versions_used": {},
            "_va_correct": 0, "_va_total": 0,
        })
        bucket["total"] += 1
        bucket[perf] = bucket.get(perf, 0) + 1
        bucket["_ret_sum"] += ret
        bucket["_comp_sum"] += comp
        if version:
            bucket["versions_used"][version] = bucket["versions_used"].get(version, 0) + 1
        if va:
            bucket["_va_total"] += 1
            if va.get("match"):
                bucket["_va_correct"] += 1

    results = []
    for bucket in skill_map.values():
        n = bucket["total"]
        bucket["win_rate"] = round(bucket["high"] / n, 2) if n else 0
        bucket["avg_retention"] = round(bucket.pop("_ret_sum") / n, 1) if n else 0
        bucket["avg_completion"] = round(bucket.pop("_comp_sum") / n, 1) if n else 0
        va_total = bucket.pop("_va_total")
        va_correct = bucket.pop("_va_correct")
        bucket["avg_verifier_accuracy"] = round(va_correct / va_total, 2) if va_total else None
        results.append(bucket)

    results.sort(key=lambda x: x["win_rate"], reverse=True)
    return results
