#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表現報告 + 未提取查詢。
"""

from .patterns import PATTERN_KEYS, load_performance_patterns


def performance_report(data):
    """生成全影片表現總覽。"""
    high, normal, low, no_backfill = [], [], [], []

    for v in data["videos"]:
        vid = v["vid"]
        bf = v.get("backfill")
        if not bf:
            # 只有已上線的影片才應該被回填，其他狀態不列入未回填清單
            if v.get("status") == "已上線":
                no_backfill.append(vid)
            continue
        perf = bf.get("performance", "normal")
        entry = {
            "vid": vid, "topic": v["topic"],
            "views": bf.get("views", 0),
            "retention_3s": bf.get("retention_3s", 0),
            "completion_rate": bf.get("completion_rate", 0),
            "engagement_rate": bf.get("engagement_rate"),
            "path": bf.get("path"),
            "learning_extracted": bf.get("learning_extracted", False),
        }
        if perf == "high":
            high.append(entry)
        elif perf == "low":
            low.append(entry)
        else:
            normal.append(entry)

    pdata = load_performance_patterns()
    opening_counts = {}
    for o in pdata.get("proven_openings", []):
        opening_counts[o.get("code", "")] = len(o.get("vid_evidence", []))
    cta_counts = {}
    for c in pdata.get("proven_ctas", []):
        cta_counts[c.get("code", "")] = len(c.get("vid_evidence", []))

    # 衰減 pattern 統計（透過 PATTERN_KEYS 驅動，不漏任何類型）
    degraded_patterns = []
    for key, id_field in PATTERN_KEYS.items():
        for item in pdata.get(key, []):
            if item.get("degraded"):
                degraded_patterns.append({
                    "type": key,
                    "code": item.get(id_field),
                    "low_evidence": item.get("low_evidence", []),
                    "degraded_date": item.get("degraded_date"),
                })

    return {
        "total": len(data["videos"]),
        "backfilled": len(high) + len(normal) + len(low),
        "high": high, "normal": normal, "low": low,
        "no_backfill": no_backfill,
        "opening_counts": opening_counts,
        "cta_counts": cta_counts,
        "risk_patterns_count": len(pdata.get("risk_patterns", [])),
        "degraded_patterns": degraded_patterns,
    }


def query_unextracted(data, include_normal=False):
    """查詢已回填但未提取學習的影片。

    預設排除 normal 表現影片（它們不需要提取學習），
    設 include_normal=True 可列出全部。
    """
    results = []
    for v in data["videos"]:
        if v.get("status") != "已上線":
            continue
        bf = v.get("backfill")
        if not bf or bf.get("learning_extracted", False):
            continue

        perf = bf.get("performance", "normal")
        if perf == "normal" and not include_normal:
            continue
        if perf == "high":
            icon = "🏆"
            action = f"提取 {v['vid']}「{v['topic']}」高表現特徵（開場/CTA/公式）→ 寫入數據大腦 [9] + performance-patterns.json"
        elif perf == "low":
            icon = "📉"
            action = f"分析 {v['vid']}「{v['topic']}」低表現原因 → 寫入 risk_patterns + 數據大腦 [9]"
        else:
            icon = "📊"
            action = f"記錄 {v['vid']}「{v['topic']}」表現數據（普通，可跳過或簡記）"

        results.append({
            "vid": v["vid"], "topic": v["topic"],
            "performance": perf,
            "views": bf.get("views", 0),
            "retention_3s": bf.get("retention_3s", 0),
            "completion_rate": bf.get("completion_rate", 0),
            "icon": icon, "action": action,
        })

    perf_order = {"high": 0, "low": 1, "normal": 2}
    results.sort(key=lambda x: perf_order.get(x["performance"], 9))
    return results
