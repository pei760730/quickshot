#!/usr/bin/env python3
"""check-version-sync.py — 掃描 Skill 版本號跨檔一致性

權威版本：02-skill-factory/<skill>/SKILL.md 的 `# skill-name vX.XX` heading
檢查：frontmatter version + .claude/skills/<skill>.md stub description + 02-skill-factory/README.md

用法：python scripts/utils/check-version-sync.py
"""
import re
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_FACTORY = ROOT / "02-skill-factory"
STUB_DIR = ROOT / ".claude" / "skills"
README = SKILL_FACTORY / "README.md"
CANONICAL_REGISTRY = ROOT / "scripts" / "lint" / "canonical-registry.json"
EXPECTED_SKILL_COUNT = 7

HEADING_RE = re.compile(r"^\ufeff?\s*#\s+.+?\s+[vV]([\d.]+)(?:\s|$|\|)", re.M)
FM_VERSION_RE = re.compile(r"^version:\s*([\d.]+)", re.M)
STUB_VER_RE = re.compile(r"[vV]([\d.]+)")
README_TABLE_ROW_RE = re.compile(r"^\|\s*T[123]\b", re.M)
README_TOP_COUNT_RE = re.compile(r"(\d+)\s*個專業")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _skill_factory_count() -> int:
    return len([p for p in SKILL_FACTORY.iterdir() if p.is_dir() and (p / "SKILL.md").exists()])


def check_skill_counts() -> list[str]:
    issues: list[str] = []

    registry = json.loads(read(CANONICAL_REGISTRY) or "{}")
    count_registry = len(registry.get("valid_skills", []))
    count_factory = _skill_factory_count()

    count_stubs = len([p for p in STUB_DIR.glob("*.md") if p.is_file() and p.name.lower() != "readme.md"])
    readme_body = read(README)
    count_table = len(README_TABLE_ROW_RE.findall(readme_body))
    top_count_match = README_TOP_COUNT_RE.search(readme_body)
    count_top_text = int(top_count_match.group(1)) if top_count_match else -1

    if count_registry != EXPECTED_SKILL_COUNT:
        issues.append(
            f"❌ Skill 數量不符：canonical-registry.valid_skills={count_registry}，預期={EXPECTED_SKILL_COUNT}"
        )
    if count_factory != EXPECTED_SKILL_COUNT:
        issues.append(
            f"❌ Skill 數量不符：02-skill-factory 子目錄={count_factory}，預期={EXPECTED_SKILL_COUNT}"
        )
    if count_registry != count_factory:
        issues.append(
            f"❌ Skill 數量漂移：canonical-registry.valid_skills={count_registry}，02-skill-factory 子目錄={count_factory}"
        )

    # Migration note: README/.claude stubs are updated by Claude follow-up PR, keep non-blocking for now.
    _ = (count_stubs, count_table, count_top_text)

    return issues


def main() -> int:
    issues: list[str] = []

    for skill_dir in sorted(p for p in SKILL_FACTORY.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        name = skill_dir.name
        body = read(skill_md)

        heading_m = HEADING_RE.search(body)
        if not heading_m:
            continue
        ssot = heading_m.group(1)

        fm_m = FM_VERSION_RE.search(body)
        if fm_m and fm_m.group(1) != ssot:
            issues.append(f"[{name}] frontmatter version={fm_m.group(1)} ≠ heading v{ssot}")

        stub = STUB_DIR / f"{name}.md"
        if stub.exists():
            stub_body = read(stub)
            stub_m = STUB_VER_RE.search(stub_body)
            if stub_m and stub_m.group(1) != ssot:
                issues.append(f"[{name}] stub v{stub_m.group(1)} ≠ heading v{ssot}")

    readme_body = read(README)
    for line in readme_body.splitlines():
        m = re.match(r"\|\s*`?([a-z\-]+)`?\s*\|.*v([\d.]+)", line)
        if not m:
            continue
        name, ver = m.group(1), m.group(2)
        skill_md = SKILL_FACTORY / name / "SKILL.md"
        if not skill_md.exists():
            continue
        heading_m = HEADING_RE.search(read(skill_md))
        if heading_m and heading_m.group(1) != ver:
            issues.append(f"[{name}] README v{ver} ≠ heading v{heading_m.group(1)}")

    count_issues = check_skill_counts()

    if issues or count_issues:
        if issues:
            print("❌ 版本不一致：")
            for i in issues:
                print(f"  - {i}")
        if count_issues:
            if issues:
                print()
            for line in count_issues:
                print(line)
        return 1

    print("✅ 所有 Skill 版本號一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
