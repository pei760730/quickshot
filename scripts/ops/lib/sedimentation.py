#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
學習沉澱：從 verifier_scores 自動偵測重複問題，產出 rule 提案（需 Kai 確認後才寫入）。
（註：本模組只讀 verifier_scores；generation_trace 目前無任何 code 消費者。）

資料來源：pipeline.json 各影片的 verifier_scores 欄位
輸出：rule_proposals list（由 Claude 展示給 Kai，確認後寫入 lessons.json
origin=verifier；v4.36 前舊路徑為 generation-rules.json、已合併）
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

# 重複次數門檻：同類問題出現 N 次以上才提議
SEDIMENTATION_THRESHOLD = 3
MAX_PROPOSALS_PER_BACKFILL = 2

# 品質問題分類表：issue_type → (判定函式, pattern 文案, rule 文案)
# 新增問題類型只需加一列、偵測與提案兩段共用此表
_ISSUE_TABLE = [
    (
        "ai_residue",
        lambda vs: bool(vs.get("ai_residue_count")) and vs["ai_residue_count"] > 0,
        "存檔時 AI 味殘留反覆出現",
        "生成腳本時加強口語化，避免書面語句式（每句≤20字，用「你」不用「我們」，避免三段式排比）",
    ),
    (
        "low_conflict",
        lambda vs: vs.get("conflict_score") is not None and vs["conflict_score"] <= 4,
        "衝突感評分反覆偏低（≤4/10）",
        "開頭3秒必須有衝突/損失/懸念元素，不用敘事鋪陳開場（參考 risk_patterns 中的「開場太慢」模式）",
    ),
    (
        "data_inconsistency",
        lambda vs: vs.get("data_consistency") is False,
        "腳本數據與數據大腦不一致反覆出現",
        "引用數字/案例前先確認在 brand.md [8][9] 中有對應記錄，無記錄則標註「⚠️ 非數據大腦素材」",
    ),
]


def _sedimentation_meta(meta=None):
    meta = meta or {}
    return (meta.get("sedimentation") or {}) if isinstance(meta, dict) else {}


def _fallback_threshold(meta=None):
    value = _sedimentation_meta(meta).get("fallback_threshold")
    if isinstance(value, int) and value > 0:
        return value
    return SEDIMENTATION_THRESHOLD


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


def propose_rules_from_verifier(pipeline_items, meta=None, operator=None):
    """分析所有影片的 verifier_scores，偵測重複品質問題。

    回傳 list[dict]，每個 dict:
    - issue_type: str (ai_residue / low_conflict / data_inconsistency)
    - count: int — 出現次數
    - vids: list[str] — 相關影片
    - proposed_rule: dict — 建議的 generation-rules 條目
    - already_exists: bool — 是否已有類似規則
    """
    # 一趟掃描、按 _ISSUE_TABLE 分類統計
    vids_by_issue = defaultdict(list)
    for item in pipeline_items:
        vid = item.get("vid")
        vs = item.get("verifier_scores")
        if not vid or not vs:
            continue
        for issue_type, detect, _, _ in _ISSUE_TABLE:
            if detect(vs):
                vids_by_issue[issue_type].append(vid)

    # 讀取現有規則，避免重複提議
    existing_rules = load_generation_rules(operator=operator)
    existing_patterns = {r.get("pattern", "") for r in existing_rules.get("avoid_patterns", [])}

    proposals = []

    threshold = _fallback_threshold(meta)
    for issue_type, _, pattern_text, rule_text in _ISSUE_TABLE:
        vids = vids_by_issue[issue_type]
        if len(vids) < threshold:
            continue
        already = pattern_text in existing_patterns or any(
            pattern_text[:20] in p for p in existing_patterns
        )
        proposals.append({
            "issue_type": issue_type,
            "count": len(vids),
            "vids": vids[:10],
            "proposed_rule": {
                "pattern": pattern_text,
                "rule": rule_text,
                "source": f"verifier_scores sedimentation {today_str()}（{len(vids)} 支影片）",
            },
            "already_exists": already,
        })

    return proposals


def get_sedimentation_context(pipeline_items, vid, operator, meta=None):
    """組裝「回填後主動沉澱」上下文，供 Claude 端判斷是否提案。

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


def apply_proposed_rule(rule_dict, operator=None):
    """將確認後的規則寫入 lessons.json（origin=verifier、stage=soft）。

    rule_dict: 應為 propose_rules_from_verifier 回傳的 proposed_rule 欄位。
    v4.36 前寫入 generation-rules.json、合併後改走 add_lesson()。
    回傳 (ok, msg)。
    """
    operator = operator or current_operator()
    existing = {r.get("pattern", "") for r in load_generation_rules(operator=operator).get("avoid_patterns", [])}
    if rule_dict.get("pattern") in existing:
        return False, f"規則已存在：{rule_dict['pattern'][:30]}..."
    add_lesson(
        operator=operator,
        origin="verifier",
        pattern=rule_dict.get("pattern"),
        counter_pattern=rule_dict.get("rule"),
        evidence=[],
        scope=[],
        stage="soft",
        source_note=rule_dict.get("source"),
    )
    total = len(load_generation_rules(operator=operator).get("avoid_patterns", []))
    return True, f"已寫入 lessons.json（共 {total} 條規則）"
