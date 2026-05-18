#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brain health snapshot — per-dimension counts only, no aggregate score.

Each dimension reports raw numbers / presence flags. Aggregation is left to
the caller (Claude reads, decides). This avoids baking a single "ready?"
threshold that does not generalize across industries.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MVP_BRAND_SECTIONS = ("[0]", "[1]", "[2.5]", "[3]", "[5]")

SECTION_HEADER_RE = re.compile(r"^## (\[[^\]]+\])\s*(.*)$")
LAST_UPDATED_RE = re.compile(r"<!--\s*last_updated:\s*(\S*)\s*-->")
TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


@dataclass
class BrandHealth:
    sections_total: int
    sections_filled: int
    mvp_filled: int
    missing_mvp: list[str] = field(default_factory=list)
    template_placeholder_present: bool = False
    mvp_total: int = len(MVP_BRAND_SECTIONS)


@dataclass
class CasesHealth:
    cases_total: int
    cases_filled: int
    template_placeholder_present: bool = False


@dataclass
class PersonasHealth:
    files_present: list[tuple[str, int]]
    primary_file: str
    primary_present: bool
    partner_file: str
    partner_present: bool


@dataclass
class OperatorsHealth:
    total_enabled: int
    operator_keys: list[str]


@dataclass
class PipelineHealth:
    items_total: int
    by_status: dict[str, int]


@dataclass
class LessonsHealth:
    soft: int
    hardened: int
    archived: int


@dataclass
class TodosHealth:
    open: int
    pending: int
    in_progress: int
    closed: int
    archived: int


@dataclass
class PatternsHealth:
    proven_openings: int
    proven_ctas: int
    proven_formulas: int
    risk_patterns: int


@dataclass
class TranscriptsHealth:
    files: int


@dataclass
class BrainHealth:
    operator: str
    brand: Optional[BrandHealth]
    cases: Optional[CasesHealth]
    personas: PersonasHealth
    operators: OperatorsHealth
    pipeline: PipelineHealth
    lessons: LessonsHealth
    todos: TodosHealth
    patterns: PatternsHealth
    transcripts: TranscriptsHealth


def _parse_sections_with_last_updated(text: str) -> list[dict]:
    sections: list[dict] = []
    current: Optional[dict] = None
    for line in text.splitlines():
        m = SECTION_HEADER_RE.match(line)
        if m:
            current = {"key": m.group(1), "name": m.group(2).strip(), "filled": False}
            sections.append(current)
            continue
        if current is None:
            continue
        lm = LAST_UPDATED_RE.search(line)
        if lm and lm.group(1):
            current["filled"] = True
    return sections


def compute_brand_health(brand_path: Path) -> Optional[BrandHealth]:
    if not brand_path.exists():
        return None
    text = brand_path.read_text(encoding="utf-8")
    sections = _parse_sections_with_last_updated(text)
    mvp_set = set(MVP_BRAND_SECTIONS)
    sections_filled = sum(1 for s in sections if s["filled"])
    mvp_filled = sum(1 for s in sections if s["key"] in mvp_set and s["filled"])
    missing_mvp = [
        f"{s['key']} {s['name']}".strip()
        for s in sections
        if s["key"] in mvp_set and not s["filled"]
    ]
    return BrandHealth(
        sections_total=len(sections),
        sections_filled=sections_filled,
        mvp_filled=mvp_filled,
        missing_mvp=missing_mvp,
        template_placeholder_present=bool(TEMPLATE_PLACEHOLDER_RE.search(text)),
    )


def compute_cases_health(cases_path: Path) -> Optional[CasesHealth]:
    if not cases_path.exists():
        return None
    text = cases_path.read_text(encoding="utf-8")
    sections = _parse_sections_with_last_updated(text)
    return CasesHealth(
        cases_total=len(sections),
        cases_filled=sum(1 for s in sections if s["filled"]),
        template_placeholder_present=bool(TEMPLATE_PLACEHOLDER_RE.search(text)),
    )


def _persona_files_for_operator(root: Path, operator: str) -> tuple[str, str]:
    """Resolve (primary, partner) persona filenames for operator.

    Delegates to brain_loader._persona_files_for_operator with a temporarily
    swapped _repo_root so the call reads `<root>/data/.operators.json`.
    """
    libs_path = PROJECT_ROOT / "scripts" / "libs"
    if str(libs_path) not in sys.path:
        sys.path.insert(0, str(libs_path))
    import brain_loader  # type: ignore

    original = brain_loader._repo_root
    brain_loader._repo_root = lambda: root
    try:
        return brain_loader._persona_files_for_operator(operator)
    finally:
        brain_loader._repo_root = original


def compute_personas_health(root: Path, operator: str) -> PersonasHealth:
    primary, partner = _persona_files_for_operator(root, operator)
    personas_dir = root / "01-data-brain" / "personas"
    files: list[tuple[str, int]] = []
    if personas_dir.exists():
        for p in sorted(personas_dir.glob("*.md")):
            try:
                files.append((p.name, len(p.read_text(encoding="utf-8"))))
            except OSError:
                continue
    return PersonasHealth(
        files_present=files,
        primary_file=primary,
        primary_present=(personas_dir / primary).exists(),
        partner_file=partner,
        partner_present=(personas_dir / partner).exists(),
    )


def compute_operators_health(operators_json: Path) -> OperatorsHealth:
    if not operators_json.exists():
        return OperatorsHealth(total_enabled=0, operator_keys=[])
    try:
        data = json.loads(operators_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return OperatorsHealth(total_enabled=0, operator_keys=[])
    ops = data.get("operators", {}) if isinstance(data, dict) else {}
    enabled = [
        k for k, v in ops.items() if isinstance(v, dict) and v.get("enabled", True)
    ]
    return OperatorsHealth(total_enabled=len(enabled), operator_keys=sorted(enabled))


def compute_pipeline_health(data_dir: Path) -> PipelineHealth:
    pipeline_json = data_dir / "pipeline.json"
    if not pipeline_json.exists():
        return PipelineHealth(items_total=0, by_status={})
    try:
        data = json.loads(pipeline_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return PipelineHealth(items_total=0, by_status={})
    items = data.get("items", []) if isinstance(data, dict) else []
    by_status: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        s = item.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    return PipelineHealth(items_total=len(items), by_status=by_status)


def compute_lessons_health(data_dir: Path) -> LessonsHealth:
    p = data_dir / "lessons.json"
    counts = {"soft": 0, "hardened": 0, "archived": 0}
    if not p.exists():
        return LessonsHealth(**counts)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return LessonsHealth(**counts)
    rows = data.get("lessons", []) if isinstance(data, dict) else []
    for r in rows:
        if not isinstance(r, dict):
            continue
        s = r.get("stage")
        if s in counts:
            counts[s] += 1
    return LessonsHealth(**counts)


def compute_todos_health(data_dir: Path) -> TodosHealth:
    p = data_dir / "todos.json"
    blank = TodosHealth(open=0, pending=0, in_progress=0, closed=0, archived=0)
    if not p.exists():
        return blank
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return blank
    todos = data.get("todos", []) if isinstance(data, dict) else []
    counts = {"pending": 0, "in_progress": 0, "closed": 0, "archived": 0}
    for t in todos:
        if not isinstance(t, dict):
            continue
        s = t.get("state")
        if s in counts:
            counts[s] += 1
    return TodosHealth(
        open=counts["pending"] + counts["in_progress"],
        pending=counts["pending"],
        in_progress=counts["in_progress"],
        closed=counts["closed"],
        archived=counts["archived"],
    )


def compute_patterns_health(data_dir: Path) -> PatternsHealth:
    p = data_dir / "performance-patterns.json"
    if not p.exists():
        return PatternsHealth(0, 0, 0, 0)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return PatternsHealth(0, 0, 0, 0)
    if not isinstance(data, dict):
        return PatternsHealth(0, 0, 0, 0)
    return PatternsHealth(
        proven_openings=len(data.get("proven_openings") or []),
        proven_ctas=len(data.get("proven_ctas") or []),
        proven_formulas=len(data.get("proven_formulas") or []),
        risk_patterns=len(data.get("risk_patterns") or []),
    )


def compute_transcripts_health(root: Path) -> TranscriptsHealth:
    d = root / "01-data-brain" / "transcripts"
    if not d.exists():
        return TranscriptsHealth(files=0)
    files = [p for p in d.glob("*.md") if p.is_file()]
    return TranscriptsHealth(files=len(files))


def _resolve_data_dir(root: Path, operator: str) -> Path:
    operators_json = root / "data" / ".operators.json"
    if not operators_json.exists():
        return root / "data" / operator
    try:
        payload = json.loads(operators_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return root / "data" / operator
    if not isinstance(payload, dict):
        return root / "data" / operator
    cfg = (payload.get("operators") or {}).get(operator)
    if isinstance(cfg, dict) and cfg.get("data_dir_rel"):
        return root / cfg["data_dir_rel"]
    return root / "data" / operator


def compute_health(operator: str, root: Optional[Path] = None) -> BrainHealth:
    root = root or PROJECT_ROOT
    data_dir = _resolve_data_dir(root, operator)
    return BrainHealth(
        operator=operator,
        brand=compute_brand_health(root / "01-data-brain" / "brand.md"),
        cases=compute_cases_health(root / "01-data-brain" / "cases.md"),
        personas=compute_personas_health(root, operator),
        operators=compute_operators_health(root / "data" / ".operators.json"),
        pipeline=compute_pipeline_health(data_dir),
        lessons=compute_lessons_health(data_dir),
        todos=compute_todos_health(data_dir),
        patterns=compute_patterns_health(data_dir),
        transcripts=compute_transcripts_health(root),
    )


def format_health_report(h: BrainHealth) -> str:
    lines: list[str] = []
    lines.append(f"🧠 大腦健康度 (operator={h.operator})")
    lines.append("")

    if h.brand is None:
        lines.append("brand.md       ❌ 缺檔（01-data-brain/brand.md 不存在）")
    else:
        b = h.brand
        pct = (b.sections_filled / b.sections_total * 100) if b.sections_total else 0
        tail = " ⚠️ 模板 placeholder 未替換" if b.template_placeholder_present else ""
        lines.append(
            f"brand.md       MVP {b.mvp_filled}/{b.mvp_total} 填、"
            f"{b.sections_filled}/{b.sections_total} sections 有內容（{pct:.0f}%）{tail}"
        )
        if b.missing_mvp:
            lines.append(f"               缺 MVP：{'、'.join(b.missing_mvp)}")

    if h.cases is None:
        lines.append("cases.md       ❌ 缺檔")
    else:
        c = h.cases
        tail = " ⚠️ 模板 placeholder 未替換" if c.template_placeholder_present else ""
        lines.append(
            f"cases.md       {c.cases_filled}/{c.cases_total} 個案例填寫{tail}"
        )

    p = h.personas
    primary_icon = "✅" if p.primary_present else "❌"
    partner_icon = "✅" if p.partner_present else "❌"
    lines.append(
        f"personas/      {primary_icon} primary={p.primary_file}、"
        f"{partner_icon} partner={p.partner_file}"
    )
    files_summary = (
        "、".join(f"{name} ({chars} chars)" for name, chars in p.files_present)
        if p.files_present
        else "（無檔案）"
    )
    lines.append(f"               檔案：{files_summary}")

    op = h.operators
    op_keys = "、".join(op.operator_keys) if op.operator_keys else "（無）"
    lines.append(f"operators      {op.total_enabled} enabled: {op_keys}")

    pl = h.pipeline
    by_status_str = (
        "、".join(f"{k}:{v}" for k, v in sorted(pl.by_status.items()))
        if pl.by_status
        else "—"
    )
    lines.append(f"pipeline       {pl.items_total} items（{by_status_str}）")

    l_ = h.lessons
    lines.append(
        f"lessons        {l_.soft} soft / {l_.hardened} hardened / {l_.archived} archived"
    )

    t = h.todos
    lines.append(
        f"todos          {t.open} open（{t.pending} pending + {t.in_progress} in_progress）"
    )

    pt = h.patterns
    lines.append(
        f"patterns       {pt.proven_openings} openings / {pt.proven_ctas} ctas / "
        f"{pt.proven_formulas} formulas / {pt.risk_patterns} risks"
    )

    tr = h.transcripts
    lines.append(f"transcripts/   {tr.files} files")

    return "\n".join(lines)
