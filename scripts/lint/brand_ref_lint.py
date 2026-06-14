#!/usr/bin/env python3
"""Lint brand.md section references used by skills and shared references."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PATH = REPO_ROOT / "01-data-brain" / "brand.md"
BRAND_SECTION_RE = re.compile(r"^##\s*\[(\d+)\]", re.MULTILINE)
# 容忍 `brand.md` [N]（反引號包裹後接空格）這種格式 —— 否則含反引號的引用會逃過偵測，
# 像 generation/SKILL.md 曾殘留的幽靈 [13]。`?\s* 吃掉收尾反引號 + 空白。
INLINE_REF_RE = re.compile(r"brand\.md`?\s*\[(\d+)\]")


def _scan_targets(repo_root: Path) -> list[Path]:
    base = repo_root / "02-skill-factory"
    files = sorted(base.glob("*/SKILL.md"))
    files.extend(sorted((base / "shared-references").glob("*.md")))
    return files


def _line_number(text: str, idx: int) -> int:
    return text[:idx].count("\n") + 1


def parse_brand_sections(brand_path: Path) -> set[int]:
    if not brand_path.exists():
        return set()
    text = brand_path.read_text(encoding="utf-8", errors="ignore")
    return {int(m.group(1)) for m in BRAND_SECTION_RE.finditer(text)}


def _parse_brand_refs_block(block: str) -> tuple[list[int], int | None]:
    for m in re.finditer(r"^brand-refs:\s*(.*)$", block, re.MULTILINE):
        after = m.group(1).strip()
        refs: list[int] = []
        if after.startswith("["):
            try:
                parsed = ast.literal_eval(after)
                if isinstance(parsed, list):
                    refs = [int(v) for v in parsed]
            except (ValueError, SyntaxError):
                refs = [int(x) for x in re.findall(r"\d+", after)]
        elif after:
            refs = [int(x) for x in re.findall(r"\d+", after)]
        else:
            start = m.end()
            for line in block[start:].splitlines():
                lm = re.match(r"^\s*-\s*(\d+)\s*$", line)
                if lm:
                    refs.append(int(lm.group(1)))
                    continue
                if line.strip() == "":
                    continue
                if re.match(r"^[^\s-]", line):
                    break
                break
        return sorted(set(refs)), _line_number(block, m.start())
    return [], None


def parse_declared_refs(text: str) -> tuple[list[int], int | None]:
    frontmatter = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    if frontmatter:
        refs, line = _parse_brand_refs_block(frontmatter.group(1))
        if refs:
            return refs, line

    tail_slice = "\n".join(text.splitlines()[-80:])
    refs, tail_line = _parse_brand_refs_block(tail_slice)
    if tail_line is None:
        return [], None
    base = max(0, len(text.splitlines()) - 80)
    return refs, base + tail_line


def parse_inline_refs(text: str) -> list[tuple[int, int]]:
    return [(int(m.group(1)), _line_number(text, m.start())) for m in INLINE_REF_RE.finditer(text)]


def run_lint(repo_root: Path | None = None) -> tuple[list[dict], dict[str, list[int]]]:
    root = repo_root or REPO_ROOT
    brand_sections = parse_brand_sections(root / "01-data-brain" / "brand.md")
    issues: list[dict] = []
    manifest: dict[str, list[int]] = {}

    for path in _scan_targets(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(root).as_posix()
        declared_refs, declared_line = parse_declared_refs(text)
        inline_refs = parse_inline_refs(text)
        inline_numbers = [n for n, _ in inline_refs]

        combined = sorted(set(declared_refs) | set(inline_numbers))
        if combined:
            manifest[rel] = combined

        for n, line in inline_refs:
            if n not in brand_sections:
                issues.append({
                    "file": str(path),
                    "line": line,
                    "severity": "ERROR",
                    "check": "brand_ref_missing_section",
                    "message": f"引用不存在的 brand.md section [{n}]",
                })

        for n in declared_refs:
            if n not in brand_sections:
                issues.append({
                    "file": str(path),
                    "line": declared_line or 0,
                    "severity": "ERROR",
                    "check": "brand_ref_missing_section",
                    "message": f"brand-refs 宣告不存在的 section [{n}]",
                })

        if declared_refs:
            missing_decl = sorted(set(inline_numbers) - set(declared_refs))
            extra_decl = sorted(set(declared_refs) - set(inline_numbers))
            if missing_decl:
                issues.append({
                    "file": str(path),
                    "line": declared_line or 0,
                    "severity": "WARN",
                    "check": "brand_ref_declaration_missing",
                    "message": f"內文有引用但 brand-refs 未宣告: {missing_decl}",
                })
            if extra_decl:
                issues.append({
                    "file": str(path),
                    "line": declared_line or 0,
                    "severity": "WARN",
                    "check": "brand_ref_overdeclared",
                    "message": f"brand-refs 宣告但內文未引用: {extra_decl}",
                })

    return issues, manifest


def _print_manifest(manifest: dict[str, list[int]], json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for path in sorted(manifest):
        print(f"{path}: {manifest[path]}")


def _print_issues(issues: Iterable[dict], repo_root: Path) -> None:
    by_file: dict[str, list[dict]] = {}
    for issue in issues:
        by_file.setdefault(issue["file"], []).append(issue)
    for file_path, file_issues in sorted(by_file.items()):
        rel = Path(file_path).relative_to(repo_root).as_posix()
        print(f"\n📄 {rel}")
        for i in sorted(file_issues, key=lambda x: x["line"]):
            icon = "❌" if i["severity"] == "ERROR" else "⚠️"
            print(f"  {icon} L{i['line']:>3} [{i['check']}] {i['message']}")


def main() -> int:
    # 強制 UTF-8 輸出：Windows / 非 UTF-8 locale 下，emoji 輸出被 pipe / pre-commit
    # 捕捉時，預設 locale codec（如 cp950）無法編碼 emoji → print 崩潰。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_mode")
    args = parser.parse_args()

    issues, manifest = run_lint(REPO_ROOT)

    if args.manifest:
        _print_manifest(manifest, args.json_mode)
        return 0

    if not issues:
        print("✅ brand-ref lint passed — 0 issues found")
        return 0

    _print_issues(issues, REPO_ROOT)
    error_count = sum(1 for i in issues if i["severity"] == "ERROR")
    warn_count = sum(1 for i in issues if i["severity"] == "WARN")
    print(f"\n結果: {error_count} errors, {warn_count} warnings")
    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
