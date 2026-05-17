#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動診斷：貼文分類 + 強弱項偵測 + 處方。
"""

from .config import (
    PERFORMANCE_THRESHOLDS, DIAGNOSIS_THRESHOLDS, today_str,
)
from .patterns import load_performance_patterns


def _classify_post_type(likes, shares, saves, engagement_rate):
    """根據互動比例分類貼文類型。"""
    likes = likes or 0
    shares = shares or 0
    saves = saves or 0
    th = DIAGNOSIS_THRESHOLDS

    # 啞彈判定：總互動率極低
    if engagement_rate is not None and engagement_rate < th["dud_engagement"]:
        return "啞彈", f"互動率{engagement_rate}%<{th['dud_engagement']}%"

    total = likes + shares + saves
    if total == 0:
        return "啞彈", "按讚/分享/收藏皆為 0"

    like_pct = round(likes / total * 100, 1)
    share_pct = round(shares / total * 100, 1)
    save_pct = round(saves / total * 100, 1)

    # 均衡型：三者差距 < 門檻
    gap = th["balanced_gap"]
    if max(like_pct, share_pct, save_pct) - min(like_pct, share_pct, save_pct) < gap:
        return "均衡型", f"按讚{like_pct}%/分享{share_pct}%/收藏{save_pct}%（差距<{gap}%）"

    # 找主導類型
    dominant = max(
        [("收藏型", save_pct, "saves"), ("分享型", share_pct, "shares"), ("按讚型", like_pct, "likes")],
        key=lambda x: x[1],
    )
    return dominant[0], f"{dominant[2]}佔互動{dominant[1]}%"


def diagnose_video(backfill_data, performance_patterns=None):
    """對回填資料自動診斷，回傳診斷 dict。

    Args:
        backfill_data: video["backfill"] dict（已含 views/retention_3s/completion_rate 等）
        performance_patterns: performance-patterns.json 的完整資料（可選，不傳會自動載入）

    Returns:
        dict: 診斷結果，寫入 backfill_data["diagnosis"]
    """
    th = DIAGNOSIS_THRESHOLDS
    if performance_patterns is None:
        performance_patterns = load_performance_patterns()

    retention_3s = backfill_data.get("retention_3s", 0)
    completion_rate = backfill_data.get("completion_rate", 0)
    engagement_rate = backfill_data.get("engagement_rate")
    likes = backfill_data.get("likes")
    shares = backfill_data.get("shares")
    saves = backfill_data.get("saves")

    diagnosis = {"diagnosed_date": today_str()}

    # ① 貼文分類
    has_interaction = likes is not None and shares is not None and saves is not None
    if has_interaction:
        post_type, post_detail = _classify_post_type(likes, shares, saves, engagement_rate)
        diagnosis["post_type"] = post_type
        diagnosis["post_type_detail"] = post_detail
    else:
        diagnosis["post_type"] = None
        missing = [f for f in ["likes", "shares", "saves"] if backfill_data.get(f) is None]
        diagnosis["missing_fields"] = missing

    # ② 強弱項偵測（結構化 key + 顯示文字）
    strengths = []
    weaknesses = []
    weakness_keys = set()  # 用結構化 key 驅動處方，不依賴顯示文字

    if retention_3s >= PERFORMANCE_THRESHOLDS["high"]["path_A"]["retention_3s_min"]:
        strengths.append(f"Hook（留存{retention_3s}%）")
    elif retention_3s < th["hook_weak"]:
        weaknesses.append(f"Hook 弱（留存{retention_3s}%<{th['hook_weak']}%）")
        weakness_keys.add("hook")

    if completion_rate >= PERFORMANCE_THRESHOLDS["high"]["path_A"]["completion_rate_min"]:
        strengths.append(f"完播（{completion_rate}%）")
    elif completion_rate < th["completion_weak"]:
        weaknesses.append(f"完播弱（{completion_rate}%<{th['completion_weak']}%）")
        weakness_keys.add("completion")

    if engagement_rate is not None:
        if engagement_rate >= th["engagement_strong"]:
            strengths.append(f"互動率（{engagement_rate}%）")
        elif engagement_rate < th["engagement_weak"]:
            weaknesses.append(f"互動弱（{engagement_rate}%<{th['engagement_weak']}%）")
            weakness_keys.add("engagement")

    diagnosis["strengths"] = strengths
    diagnosis["weaknesses"] = weaknesses

    # ③ 處方（從 performance-patterns.json 撈，排除 degraded）
    prescriptions = []

    def _pick_best(items, label_fn):
        """從 items 中挑最佳推薦，優先排除 degraded。"""
        healthy = [i for i in items if not i.get("degraded")]
        pool = healthy or items  # 全部衰減時 fallback，但會加警告
        if not pool:
            return None, False
        best = max(pool, key=lambda x: len(x.get("vid_evidence", [])))
        evidence = best.get("vid_evidence", [])
        if not evidence:
            return None, False
        vids = ", ".join(evidence[:3])
        label = label_fn(best, len(evidence), vids)
        if not healthy and items:
            label += "（⚠️ 該 pattern 已衰減，謹慎參考）"
        return label, True

    # Hook 弱 → 推薦 proven_openings
    if "hook" in weakness_keys:
        openings = performance_patterns.get("proven_openings", [])
        label, found = _pick_best(
            openings,
            lambda b, n, v: f"開場建議用 {b['code']}（{n}次高表現：{v}）",
        )
        prescriptions.append(label if found else "開場建議加衝突感/數字（樣本不足，暫無成功案例對照）")

    # 完播弱 → 推薦 proven_formulas
    if "completion" in weakness_keys:
        formulas = performance_patterns.get("proven_formulas", [])
        label, found = _pick_best(
            formulas,
            lambda b, n, v: f"公式參考：「{b['formula']}」（{n}次驗證：{v}）",
        )
        prescriptions.append(label if found else "建議加強節奏感與情緒轉折（樣本不足，暫無公式對照）")

    # 互動弱 → 推薦 proven_ctas
    if "engagement" in weakness_keys:
        ctas = performance_patterns.get("proven_ctas", [])
        label, found = _pick_best(
            ctas,
            lambda b, n, v: f"CTA 建議用 {b['code']}（{n}次高表現：{v}）",
        )
        prescriptions.append(label if found else "建議加明確 CTA 引導（樣本不足，暫無成功案例對照）")

    diagnosis["prescriptions"] = prescriptions
    return diagnosis
