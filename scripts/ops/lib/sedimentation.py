#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
學習沉澱（v5.x「縮」後）：只負責組裝「回填後的歷史脈絡」供 Claude 在對話中
**手動**判斷是否需要記一條 lesson。

v5.x 砍除「自動從 verifier_scores 偵測重複問題 → 自動產出 rule 提案」那條
自動迴圈（propose_rules_from_verifier / apply_proposed_rule）—— 它屬於短期客戶
不需要的跨時間自我進化機器、且實務上從未真正被採用。改由 Claude 看 context
自己判斷、要記就走手動 `記錯` / `/harden`。

資料來源：pipeline.json 各影片的 verifier_scores / backfill 欄位
輸出：get_sedimentation_context() 的結構化脈絡（similar videos + avoid_patterns
+ risk_patterns + ungraduated_mistakes），純供 Claude 對話參考。
"""

from collections import defaultdict

from . import config as _cfg
from .config import today_str, current_operator
from .lessons import add_lesson, load_lessons
from .storage import load_json

_EMPTY_RULES = {
    "description": "從下游學到的生成規則（wrapper over lessons.json、v4.36 前為 generation-rules.json）— verifier 沉澱 + humanizer / quality 修正 + manual + graduated_mistake 等 origin 的 soft lessons，generation skill 生成時預載",
    "avoid_patterns": [],
}

# 同一次回填最多請 Claude 考慮的歷史脈絡提示數（手動判斷用、非自動提案）
MAX_PROPOSALS_PER_BACKFILL = 2


def _sedimentation_meta(meta=None):
    meta = meta or {}
    return (meta.get("sedimentation") or {}) if isinstance(meta, dict) else {}


def _max_proposals(meta=None):
    value = _sedimentation_meta(meta).get("max_proposals_per_backfill")
    if isinstance(value, int) and value > 0:
        return value
    return MAX_PROPOSALS_PER_BACKFILL

def _performance_patterns_path():
    return _cfg.PERFORMANCE_PATTERNS_JSON


def load_generation_rules(operator=None):
    operator = operator or current_operator()
    lessons = load_lessons(operator)
    avoid = []
    for item in lessons:
        if item.get("origin") not in {"verifier", "humanizer", "quality", "manual", "graduated_mistake"}:
            continue
        scope = item.get("scope") or []
        if isinstance(scope, str):
            scope = [scope]
        if scope and "generation" not in scope:
            continue
        avoid.append(
            {
                "pattern": item.get("pattern"),
                "rule": item.get("counter_pattern"),
                "source": item.get("source_note") or f"lessons:{item.get('id')}",
            }
        )
    return {"description": _EMPTY_RULES["description"], "avoid_patterns": avoid}


def save_generation_rules(data, operator=None):
    operator = operator or current_operator()
    for rule in data.get("avoid_patterns", []):
        add_lesson(
            operator=operator,
            origin="verifier",
            pattern=rule.get("pattern"),
            counter_pattern=rule.get("rule"),
            evidence=[],
            scope=[],
            stage="soft",
            source_note=rule.get("source"),
        )


def get_sedimentation_context(pipeline_items, vid, operator, meta=None):
    """組裝「回填後的歷史脈絡」供 Claude 在對話中**手動**判斷是否需記 lesson。

    （v5.x「縮」：原本還搭配 propose_rules_from_verifier 自動提案、已移除。
    本函式純提供脈絡、不再驅動自動規則生成。）

    回傳 dict：
    - target_video: 本次 VID 的核心資料
    - recent_similar_videos: 最近 10 支同類影片（優先同 hook/type/version）
    - avoid_patterns: lessons.json 中 origin ∈ {verifier, humanizer, quality, manual, graduated_mistake} 的 soft lessons（v4.36 前為 generation-rules.json）
    - risk_patterns: performance-patterns risk_patterns
    - ungraduated_mistakes: lessons.json 中 origin=mistake 且 stage=soft 的項目（v4.36 前為 claude-mistakes graduated=false 項）
    """
    target = None
    for item in pipeline_items:
        if item.get("vid") == vid:
            target = item
            break
    if target is None:
        return {
            "error": f"VID not found: {vid}",
            "vid": vid,
            "operator": operator,
        }

    def _is_similar(item):
        if item.get("vid") == vid:
            return False
        if not item.get("vid"):
            return False
        # 優先看 script metadata；沒有時退回 tags/source
        same_hook = bool(target.get("hook_type")) and item.get("hook_type") == target.get("hook_type")
        same_ver = bool(target.get("version")) and item.get("version") == target.get("version")
        same_title = bool(target.get("title_type")) and item.get("title_type") == target.get("title_type")
        same_tags = bool(target.get("tags")) and item.get("tags") == target.get("tags")
        same_source = bool(target.get("source")) and item.get("source") == target.get("source")
        return same_hook or same_ver or same_title or same_tags or same_source

    def _recent_key(item):
        bf = item.get("backfill") or {}
        return (
            bf.get("backfilled_date")
            or item.get("publish_date")
            or item.get("save_date")
            or item.get("created_date")
            or ""
        )

    similar = [i for i in pipeline_items if _is_similar(i)]
    similar_sorted = sorted(similar, key=_recent_key, reverse=True)[:10]

    rules = load_generation_rules(operator=operator)
    pp = load_json(
        _performance_patterns_path(),
        {"risk_patterns": []},
        label="performance-patterns",
    )
    # v2.0 schema: "mistake" origin lives in `soft` stage (was observation/candidate/active in v1.x)
    # "graduated_mistake" origin is emitted when a mistake graduates; we filter by origin here.
    active_mistakes = [
        m for m in load_lessons(operator)
        if m.get("origin") == "mistake" and m.get("stage") == "soft"
    ]

    return {
        "date": today_str(),
        "operator": operator,
        "vid": vid,
        "limits": {"max_proposals": _max_proposals(meta)},
        "target_video": {
            "vid": target.get("vid"),
            "topic": target.get("topic"),
            "tags": target.get("tags"),
            "hook_type": target.get("hook_type"),
            "title_type": target.get("title_type"),
            "version": target.get("version"),
            "verifier_scores": target.get("verifier_scores"),
            "backfill": target.get("backfill"),
        },
        "recent_similar_videos": [
            {
                "vid": item.get("vid"),
                "topic": item.get("topic"),
                "tags": item.get("tags"),
                "hook_type": item.get("hook_type"),
                "title_type": item.get("title_type"),
                "version": item.get("version"),
                "verifier_scores": item.get("verifier_scores"),
                "backfill": item.get("backfill"),
            }
            for item in similar_sorted
        ],
        "avoid_patterns": rules.get("avoid_patterns", []),
        "risk_patterns": pp.get("risk_patterns", []),
        "ungraduated_mistakes": active_mistakes,
    }
