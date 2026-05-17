#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified Step-0 brain loader for skills."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass
class BrainBundle:
    brand_md: str
    cases_md: str
    kai_md: str
    an_md: str
    performance_patterns: dict[str, Any]
    lessons: list[dict[str, Any]]
    banned_words: list[str]


LEGACY_SKILLS = {
    "harden",
    "skill-creator",
}

CORE_VNEXT_SKILLS = {
    "orientation",
    "discovery",
    "generation",
    "quality",
    "distillation",
}

GENERATION_MODE_SCOPE = {
    "orientation": ["orientation"],
    "discover-trend": ["discovery"],
    "dual-track": ["generation"],
    "quality-gate": ["quality"],
    "distillation": ["distillation"],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _operator_data_dir(operator: str) -> Path:
    root = _repo_root()
    operators_json = root / "data" / ".operators.json"
    if operators_json.exists():
        try:
            payload = json.loads(operators_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        cfg = (
            (payload.get("operators") or {}).get(operator)
            if isinstance(payload, dict)
            else None
        )
        if isinstance(cfg, dict):
            return root / cfg.get("data_dir_rel", f"data/{operator}")
    return root / "data" / operator


def _load_required_text(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"required brain file missing: {label} ({path})")
    return path.read_text(encoding="utf-8")


def _load_optional_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _parse_banned_words(text: str) -> list[str]:
    words = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith(("-", "*")):
            s = s[1:].strip()
        if s:
            words.append(s)
    return words


def _active_lessons(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("stage") == "soft"]


def _normalize_scope(raw_scope: Any) -> list[str]:
    if isinstance(raw_scope, str):
        return [raw_scope]
    if isinstance(raw_scope, list):
        return [s for s in raw_scope if isinstance(s, str)]
    return []


def _filter_lessons(
    rows: list[dict[str, Any]], scopes: list[str] | None
) -> list[dict[str, Any]]:
    active_rows = _active_lessons(rows)
    if not scopes:
        return active_rows

    target = set(scopes)
    filtered = []
    for row in active_rows:
        scope = _normalize_scope(row.get("scope"))
        if scope and target.isdisjoint(scope):
            continue
        filtered.append(row)
    return filtered


def _resolve_vnext_scopes(
    skill_name: str, mode: str | None, phase: str | None
) -> list[str] | None:
    # graceful fallback when mode/phase is missing
    if skill_name in {"orientation", "discovery"} and not mode:
        return None
    if skill_name == "generation":
        if not mode:
            return None
        return GENERATION_MODE_SCOPE.get(mode, [mode, "generation"])
    if skill_name == "quality":
        if not phase:
            return None
        return [phase, "quality"]
    if skill_name == "distillation":
        return ["distillation", "generation"]
    return None


def load_for_skill(
    operator: str, skill_name: str, mode: str | None = None, phase: str | None = None
) -> BrainBundle:
    root = _repo_root()
    data_dir = _operator_data_dir(operator)

    brand_md = _load_required_text(root / "01-data-brain" / "brand.md", "brand.md")
    cases_md = _load_required_text(root / "01-data-brain" / "cases.md", "cases.md")
    personas_dir = root / "01-data-brain" / "personas"
    kai_path = personas_dir / "kai.md"
    kai_md = kai_path.read_text(encoding="utf-8") if kai_path.exists() else ""
    an_path = personas_dir / "an.md"
    an_md = an_path.read_text(encoding="utf-8") if an_path.exists() else ""

    perf = _load_optional_json(
        data_dir / "performance-patterns.json",
        {
            "proven_openings": [],
            "proven_ctas": [],
            "proven_formulas": [],
            "risk_patterns": [],
        },
    )
    if skill_name == "discovery" and mode == "discover-trend":
        perf = dict(perf)
        perf.setdefault("web_fetch_placeholder", {"enabled": True})

    lessons_payload = _load_optional_json(data_dir / "lessons.json", {"lessons": []})
    lessons = (
        lessons_payload.get("lessons") if isinstance(lessons_payload, dict) else []
    )
    if not isinstance(lessons, list):
        lessons = []

    if skill_name in LEGACY_SKILLS:
        lessons = _filter_lessons(lessons, [skill_name, "generation"])
    elif skill_name in CORE_VNEXT_SKILLS:
        lessons = _filter_lessons(
            lessons, _resolve_vnext_scopes(skill_name, mode, phase)
        )
        if skill_name == "distillation":
            preferred = [
                r for r in lessons if "distillation" in _normalize_scope(r.get("scope"))
            ]
            lessons = preferred or lessons
    else:
        lessons = _filter_lessons(lessons, None)

    banned_path = root / "02-skill-factory" / "shared-references" / "banned-words.md"
    banned_words = (
        _parse_banned_words(banned_path.read_text(encoding="utf-8"))
        if banned_path.exists()
        else []
    )

    return BrainBundle(
        brand_md=brand_md,
        cases_md=cases_md,
        kai_md=kai_md,
        an_md=an_md,
        performance_patterns=perf,
        lessons=lessons,
        banned_words=banned_words,
    )
