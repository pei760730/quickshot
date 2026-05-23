#!/usr/bin/env python3
"""Lint generated script IO contract."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "docs" / "contracts" / "skill-io-schema.md"

DEFAULT_SPEC = {
    "frontmatter_required": ["vid", "skill", "skill_version", "generated_at"],
    "sections_by_skill": {
        "generation": ["核心腳本"],
        "quality": ["Verifier 結果"],
    },
}

SKILL_FILE_MAP = {
    "generation": "02-skill-factory/generation/SKILL.md",
    "quality": "02-skill-factory/quality/SKILL.md",
}
OUTPUT_CONTRACT_HEADING_RE = re.compile(r"^##\s+Output\s+Contract", re.MULTILINE)


def _parse_contract() -> dict:
    if not CONTRACT.exists():
        return DEFAULT_SPEC
    text = CONTRACT.read_text(encoding="utf-8")
    spec = {"frontmatter_required": [], "sections_by_skill": {}}

    table_rows = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            table_rows.append(cells)

    header = []
    for row in table_rows:
        if not row:
            continue
        first = row[0].strip().lower()
        if first in {"---", "------"} or set(first) == {"-"}:
            continue
        if first in {"field", "欄位", "命令", "面向", "skill"} and any(
            "required" in c.lower() or "必填" in c for c in row
        ):
            header = [c.strip().lower() for c in row]
            continue

        if header and "field" in " ".join(header) and "required" in " ".join(header):
            req_idx = next((i for i, h in enumerate(header) if "required" in h), 2)
            field_idx = next(
                (i for i, h in enumerate(header) if "field" in h or "欄位" in h), 0
            )
            required = (row[req_idx] if len(row) > req_idx else "").strip().lower()
            field = row[field_idx].strip()
            if required in {"yes", "y", "required", "必填", "✅"} and re.fullmatch(
                r"[a-z_][a-z0-9_]*", field
            ):
                spec["frontmatter_required"].append(field)
            continue

        if re.fullmatch(r"[a-z][a-z0-9\-]+", row[0].strip()):
            skill = row[0].strip()
            sections_blob = row[1] if len(row) >= 2 else ""
            sections = [
                x.strip(" `") for x in re.split(r"[+,，、]", sections_blob) if x.strip()
            ]
            if sections:
                spec["sections_by_skill"][skill] = sections

    spec["frontmatter_required"] = sorted(set(spec["frontmatter_required"]))
    if not spec["frontmatter_required"]:
        spec["frontmatter_required"] = DEFAULT_SPEC["frontmatter_required"]
    if not spec["sections_by_skill"]:
        spec["sections_by_skill"] = DEFAULT_SPEC["sections_by_skill"]
    return spec


def _parse_validation_rule_ids() -> set[str]:
    if not CONTRACT.exists():
        return set()
    text = CONTRACT.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*-\s+id:\s*([a-z0-9_]+)\s*$", text, flags=re.MULTILINE))


def _parse_frontmatter(text: str) -> tuple[dict, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 1
    front = {}
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return front, idx + 1
        if ":" in lines[idx]:
            k, v = lines[idx].split(":", 1)
            front[k.strip()] = v.strip()
    return front, 1


def _extract_sections(text: str) -> set[str]:
    secs = set()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            secs.add(s[3:].strip())
    return secs


def _extract_output_contract_section(text: str) -> tuple[bool, str]:
    m = OUTPUT_CONTRACT_HEADING_RE.search(text)
    if not m:
        return False, ""
    section_start = m.end()
    next_heading = re.search(r"^##\s+", text[section_start:], flags=re.MULTILINE)
    if not next_heading:
        return True, text[section_start:]
    return True, text[section_start : section_start + next_heading.start()]


def _lint_output_contract_sections(rule_ids: set[str]) -> list[dict]:
    errors: list[dict] = []
    check_generation = "output_contract_section_present" in rule_ids
    check_quality = "quality_output_contract_present" in rule_ids
    if not check_generation and not check_quality:
        return errors

    if check_generation:
        skill_file = REPO_ROOT / SKILL_FILE_MAP["generation"]
        if not skill_file.exists():
            errors.append(
                {
                    "file": str(skill_file),
                    "line": 1,
                    "severity": "ERROR",
                    "check": "output_contract_section_present",
                    "message": f"generation missing SKILL.md: {SKILL_FILE_MAP['generation']}",
                }
            )
        else:
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
            heading_ok, section = _extract_output_contract_section(content)
            if not heading_ok:
                errors.append(
                    {
                        "file": str(skill_file),
                        "line": 1,
                        "severity": "ERROR",
                        "check": "output_contract_section_present",
                        "message": "generation missing heading: ## Output Contract",
                    }
                )
            elif "--skill generation" not in section or "--mode" not in section:
                errors.append(
                    {
                        "file": str(skill_file),
                        "line": 1,
                        "severity": "ERROR",
                        "check": "output_contract_section_present",
                        "message": "generation Output Contract must mention --skill generation and --mode",
                    }
                )

    if check_quality:
        skill_file = REPO_ROOT / SKILL_FILE_MAP["quality"]
        if not skill_file.exists():
            errors.append(
                {
                    "file": str(skill_file),
                    "line": 1,
                    "severity": "ERROR",
                    "check": "quality_output_contract_present",
                    "message": f"quality missing SKILL.md: {SKILL_FILE_MAP['quality']}",
                }
            )
            return errors

        content = skill_file.read_text(encoding="utf-8", errors="ignore")
        heading_ok, section = _extract_output_contract_section(content)
        if not heading_ok:
            errors.append(
                {
                    "file": str(skill_file),
                    "line": 1,
                    "severity": "ERROR",
                    "check": "quality_output_contract_present",
                    "message": "quality missing heading: ## Output Contract",
                }
            )
        elif "record-verifier-scores" not in section or "phase=check" not in content:
            errors.append(
                {
                    "file": str(skill_file),
                    "line": 1,
                    "severity": "ERROR",
                    "check": "quality_output_contract_present",
                    "message": "quality Output Contract must mention record-verifier-scores and phase=check",
                }
            )
    return errors


def run_lint() -> list[dict]:
    spec = _parse_contract()
    rule_ids = _parse_validation_rule_ids()
    errors = []
    for path in (REPO_ROOT / "03-production-line").glob("**/*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        front, start_line = _parse_frontmatter(text)
        if not front:
            continue
        for field in spec["frontmatter_required"]:
            if not front.get(field):
                errors.append(
                    {
                        "file": str(path),
                        "line": 1,
                        "severity": "ERROR",
                        "check": "skill_io_frontmatter",
                        "message": f"missing required frontmatter field: {field}",
                    }
                )
        skill = front.get("skill")
        if not skill:
            continue
        sections = _extract_sections(text)
        for sec in spec["sections_by_skill"].get(skill, []):
            if sec not in sections:
                errors.append(
                    {
                        "file": str(path),
                        "line": start_line,
                        "severity": "ERROR",
                        "check": "skill_io_sections",
                        "message": f"missing required section for {skill}: {sec}",
                    }
                )
    errors.extend(_lint_output_contract_sections(rule_ids))
    return errors


def main() -> int:
    issues = run_lint()
    if issues:
        for i in issues:
            print(
                f"[{i['severity']}] {i['file']}:{i['line']} {i['check']} - {i['message']}"
            )
        return 1
    print("✅ skill-io lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
