#!/usr/bin/env python3
"""Warn-only lint for deterministic AI-writing patterns."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERNS = {
    13: "em dash overuse",
    14: "mechanical boldface",
    17: "emoji bullet start",
    19: "chatbot artifacts",
    20: "cutoff disclaimers",
    24: "generic positive conclusions",
}

CHATBOT_RE = re.compile(r"(I hope this helps|Of course!|Certainly!|Let me know|Here is a)", re.IGNORECASE)
CUTOFF_RE = re.compile(r"(as of\s+\w+\s+\d{4}|up to my last training update|while specific details are limited)", re.IGNORECASE)
POSITIVE_RE = re.compile(r"(the future looks bright|exciting times lie ahead|a step in the right direction)", re.IGNORECASE)


def lint_text(text: str) -> list[tuple[int, int, str]]:
    findings: list[tuple[int, int, str]] = []
    lines = text.splitlines()

    paragraph = []
    para_start = 1
    for idx, line in enumerate(lines + [""], start=1):
        if line.strip():
            if not paragraph:
                para_start = idx
            paragraph.append(line)
        else:
            if paragraph:
                block = "\n".join(paragraph)
                if block.count("—") >= 3:
                    findings.append((13, para_start, paragraph[0].strip()))
                paragraph = []

    run_start = None
    run_count = 0
    for idx, line in enumerate(lines, start=1):
        if "**" in line:
            if run_start is None:
                run_start = idx
            run_count += 1
        else:
            if run_count >= 3:
                findings.append((14, run_start, lines[run_start - 1].strip()))
            run_start = None
            run_count = 0
    if run_count >= 3 and run_start is not None:
        findings.append((14, run_start, lines[run_start - 1].strip()))

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("- 🚀") or stripped.startswith("- 💡") or stripped.startswith("- ✅"):
            findings.append((17, idx, stripped))
        if CHATBOT_RE.search(line):
            findings.append((19, idx, stripped))
        if CUTOFF_RE.search(line):
            findings.append((20, idx, stripped))
        if POSITIVE_RE.search(line):
            findings.append((24, idx, stripped))

    return findings


def lint_path(path: Path) -> list[str]:
    warns = []
    for md in sorted(path.rglob("*.md")):
        findings = lint_text(md.read_text(encoding="utf-8"))
        for n, ln, quote in findings:
            warns.append(f"⚠️ AI pattern #{n} at line {ln}: {quote[:120]} ({md})")
    return warns


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--path", default="03-production-line/02-ready-to-shoot/")
    args = parser.parse_args()
    warns = lint_path(Path(args.path))
    for w in warns:
        print(w)
    print(f"AI patterns lint finished: {len(warns)} warnings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
