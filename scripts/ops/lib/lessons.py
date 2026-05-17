#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified lessons storage (v2.0 schema, engine v4.63+).

Schema v2.0（Opus 4.7 全修 Stage C）:
- stage 三態：soft / hardened / archived
  - soft = 預載、可能影響下次生成（原 observation/candidate/active 合併）
  - hardened = 已轉為 test / lint / CLAUDE.md 禁令 / brand.md（不再預載）
  - archived = 終態、誤判或已被取代
- 欄位：id / origin / stage / pattern / counter_pattern / evidence / scope /
        source_note / created_at / updated_at
- 已刪（v1.1 假智能欄位）：hit_count / last_hit_at / hardening_status / confidence
"""

from copy import deepcopy
import re

from . import config as _cfg
from .config import today_str
from .storage import load_json, save_json

VALID_STAGES = {"soft", "hardened", "archived"}
VALID_ORIGINS = {
    "mistake",
    "deviation",
    "verifier",
    "humanizer",  # historical (humanizer skill 已退役、保留為合法 origin)
    "quality",    # new (Phase 5 後)
    "manual",
    "graduated_mistake",
    "deviation_analysis",
}

_ID_RE = re.compile(r"^L-(\d{4,})$")
_VID_RE = re.compile(r"^VID-\d+$")

_EMPTY = {
    "schema_version": "2.0",
    "description": "Unified lessons — soft (預載) / hardened (已轉 test/lint/brand/禁令) / archived",
    "next_id": 1,
    "lessons": [],
}


def _lessons_json(operator=None):
    paths = _cfg.get_operator_paths(operator)
    return paths["data_dir"] / "lessons.json"


def _ensure_scope(scope):
    if scope is None:
        return []
    if isinstance(scope, list):
        return [str(x) for x in scope if str(x).strip()]
    if isinstance(scope, str):
        s = scope.strip()
        return [s] if s else []
    return [str(scope)]


def _normalize_stage(stage):
    if stage not in VALID_STAGES:
        raise ValueError(f"invalid stage: {stage} (expected one of {sorted(VALID_STAGES)})")
    return stage


def _normalize_origin(origin):
    if origin not in VALID_ORIGINS:
        raise ValueError(f"invalid origin: {origin}")
    return origin


def _load_payload(operator=None):
    raw = load_json(_lessons_json(operator), deepcopy(_EMPTY), label="lessons")

    lessons = raw.get("lessons")
    if not isinstance(lessons, list):
        lessons = raw.get("entries", []) if isinstance(raw.get("entries"), list) else []

    next_id = raw.get("next_id")
    if not isinstance(next_id, int) or next_id <= 0:
        max_id = 0
        for row in lessons:
            m = _ID_RE.match(str(row.get("id", "")))
            if m:
                max_id = max(max_id, int(m.group(1)))
        next_id = max_id + 1 if max_id > 0 else 1

    payload = {
        "schema_version": str(raw.get("schema_version") or "2.0"),
        "description": raw.get("description") or _EMPTY["description"],
        "next_id": next_id,
        "lessons": lessons,
    }

    # Normalize shape + gentle v1.x → v2.0 auto-migration on load
    # (lazy migration only; one-shot migrate_lessons_to_v2.py retired in v4.70)
    for item in payload["lessons"]:
        item["scope"] = _ensure_scope(item.get("scope"))
        if not isinstance(item.get("evidence"), list):
            item["evidence"] = [] if item.get("evidence") is None else [item.get("evidence")]

        raw_stage = item.get("stage") or "soft"
        if raw_stage in VALID_STAGES:
            item["stage"] = raw_stage
        elif raw_stage in ("observation", "candidate", "active"):
            item["stage"] = "soft"
        elif raw_stage == "graduated":
            item["stage"] = "hardened"
        else:
            item["stage"] = "soft"

        # Drop any residual v1.x fields
        for legacy_key in ("hit_count", "last_hit_at", "hardening_status", "confidence"):
            item.pop(legacy_key, None)

    return payload


def _save_payload(operator, payload):
    save_json(_lessons_json(operator), payload, update_meta=False)


def load_lessons(operator=None):
    return _load_payload(operator)["lessons"]


def save_lessons(operator, lessons):
    payload = _load_payload(operator)
    payload["lessons"] = lessons
    _save_payload(operator, payload)


def _allocate_lesson_id(payload):
    lesson_id = f"L-{payload['next_id']:04d}"
    payload["next_id"] += 1
    return lesson_id


def add_lesson(
    operator,
    origin,
    pattern,
    counter_pattern=None,
    evidence=None,
    scope=None,
    stage="soft",
    source_note=None,
):
    """Add or merge a lesson.

    If (origin, pattern) already exists: merge evidence, refresh timestamps,
    update counter_pattern/scope/source_note if provided. Stage can only move
    soft → hardened or soft → archived (monotonic, enforced by promote_stage).
    """
    origin = _normalize_origin(origin)
    stage = _normalize_stage(stage)
    pattern = (pattern or "").strip()
    if not pattern:
        raise ValueError("pattern is required")

    evidence = evidence or []
    if not isinstance(evidence, list):
        evidence = [evidence]
    norm_scope = _ensure_scope(scope)

    now = today_str()
    payload = _load_payload(operator)
    lessons = payload["lessons"]

    for item in lessons:
        if item.get("origin") == origin and item.get("pattern") == pattern:
            merged = list(item.get("evidence") or [])
            seen = {str(x) for x in merged}
            for ev in evidence:
                if str(ev) not in seen:
                    merged.append(ev)
                    seen.add(str(ev))
            item["evidence"] = merged

            current_stage = item.get("stage", "soft")
            if stage != current_stage and _can_promote(current_stage, stage):
                item["stage"] = stage

            if counter_pattern is not None:
                item["counter_pattern"] = counter_pattern
            if scope is not None:
                item["scope"] = norm_scope
            if source_note is not None:
                item["source_note"] = source_note
            item["updated_at"] = now
            _save_payload(operator, payload)
            return item.get("id")

    lesson_id = _allocate_lesson_id(payload)
    lessons.append(
        {
            "id": lesson_id,
            "origin": origin,
            "pattern": pattern,
            "counter_pattern": counter_pattern,
            "evidence": evidence,
            "scope": norm_scope,
            "stage": stage,
            "source_note": source_note,
            "created_at": now,
            "updated_at": now,
        }
    )
    _save_payload(operator, payload)
    return lesson_id


def _can_promote(current_stage, new_stage):
    """v2.0 transitions: soft → hardened/archived; terminal states can't change."""
    if current_stage == new_stage:
        return True
    if current_stage in ("hardened", "archived"):
        return False  # terminal
    # current == "soft"
    return new_stage in ("hardened", "archived")


def promote_stage(operator, lesson_id, new_stage):
    new_stage = _normalize_stage(new_stage)
    payload = _load_payload(operator)

    for item in payload["lessons"]:
        if item.get("id") != lesson_id:
            continue
        current = item.get("stage", "soft")
        if not _can_promote(current, new_stage):
            raise ValueError(
                f"invalid stage transition: {current} → {new_stage} "
                f"(v2.0 only allows soft → hardened/archived)"
            )
        if new_stage != current:
            item["stage"] = new_stage
            item["updated_at"] = today_str()
            _save_payload(operator, payload)
        return True
    return False


def archive_lesson(operator, lesson_id, reason=None):
    """Archive a lesson. If reason provided, append stamp to source_note."""
    payload = _load_payload(operator)
    for item in payload["lessons"]:
        if item.get("id") != lesson_id:
            continue
        if item.get("stage") == "archived":
            return False
        item["stage"] = "archived"
        item["updated_at"] = today_str()
        if reason:
            stamp = f"archived {today_str()}: {reason.strip()}"
            existing = (item.get("source_note") or "").strip()
            item["source_note"] = f"{existing}; {stamp}" if existing else stamp
        _save_payload(operator, payload)
        return True
    return False


def add_evidence(operator, lesson_id, vid):
    """Append a VID to lesson evidence list (idempotent)."""
    vid = (vid or "").strip()
    if not _VID_RE.match(vid):
        raise ValueError(f"invalid vid format: {vid} (expected VID-<digits>)")

    payload = _load_payload(operator)
    for item in payload["lessons"]:
        if item.get("id") != lesson_id:
            continue
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            evidence = [] if evidence is None else [evidence]
        if vid in evidence:
            return {"ok": True, "found": True, "added": False, "evidence_count": len(evidence)}
        evidence.append(vid)
        item["evidence"] = evidence
        item["updated_at"] = today_str()
        _save_payload(operator, payload)
        return {"ok": True, "found": True, "added": True, "evidence_count": len(evidence)}

    return {"ok": False, "found": False, "added": False, "evidence_count": 0}


def lessons_stats(operator):
    """Return simple stage-grouped counts (v2.0)."""
    rows = load_lessons(operator)
    by_stage = {"soft": 0, "hardened": 0, "archived": 0}
    for row in rows:
        st = row.get("stage", "soft")
        by_stage[st] = by_stage.get(st, 0) + 1
    return {
        "total": len(rows),
        "by_stage": by_stage,
    }


def stats(operator):
    """Backward-compatible alias."""
    return lessons_stats(operator)


def propose_hardening(operator):
    """Return soft lessons with a non-empty counter_pattern (hardening candidates).

    v2.0 change: no hit_count threshold. Claude decides in-conversation which
    lessons should be hardened based on observed friction, then runs /harden
    (Stage D) or manually writes the corresponding test/lint/禁令/brand diff.
    """
    rows = load_lessons(operator)
    result = []
    for row in rows:
        if row.get("stage") != "soft":
            continue
        cp = (row.get("counter_pattern") or "").strip()
        if not cp:
            continue
        result.append(row)
    return result


def query(operator, origin=None, scope=None, stage=None):
    data = load_lessons(operator)
    result = []
    scope_filter = _ensure_scope(scope)
    for item in data:
        if origin and item.get("origin") != origin:
            continue
        if stage and item.get("stage") != stage:
            continue
        if scope_filter:
            item_scope = _ensure_scope(item.get("scope"))
            if not set(scope_filter).issubset(set(item_scope)):
                continue
        result.append(item)
    return result
