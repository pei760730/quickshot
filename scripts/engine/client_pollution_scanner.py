"""客戶污染掃描 — 從 CLAUDE.local.md 讀客戶自填 forbidden_terms、不寫死。

對應 L-0022 第三層防護。原本 Q5 patterns 寫死「紅茶巴士/阿檸/800 杯」、
對其他客戶失效。改成讀客戶 config、Kai 自己 repo 在 PR-4 補對應 section。
"""
from __future__ import annotations

import re
from pathlib import Path

POLLUTION_MARKER_START = "<!-- POLLUTION_PATTERNS_START -->"
POLLUTION_MARKER_END = "<!-- POLLUTION_PATTERNS_END -->"

SCAN_PATHS_DEFAULT: tuple[str, ...] = (
    "01-data-brain/**/*.md",
    "00-control-center/**/*.md",
    "CLAUDE.local.md",
)
SCAN_EXCLUDE_DEFAULT: tuple[str, ...] = (
    "01-data-brain/index.md",
    "CLAUDE.local.md",  # 自身會含 forbidden_terms 字面、不掃
)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


def load_forbidden_terms(claude_local_md: Path) -> list[str]:
    """從 CLAUDE.local.md 解析 forbidden_terms。

    格式：在 START/END marker 之間的 markdown bullet list。
    無檔 / 無 marker / 空 list → 回 []。
    """
    if not claude_local_md.exists():
        return []
    content = claude_local_md.read_text(encoding="utf-8")
    s = content.find(POLLUTION_MARKER_START)
    e = content.find(POLLUTION_MARKER_END)
    if s == -1 or e == -1 or e <= s:
        return []
    block = content[s + len(POLLUTION_MARKER_START) : e]
    terms: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            term = line[2:].strip()
            if term:
                terms.append(term)
    return terms


def scan_pollution(
    repo_root: Path,
    forbidden_terms: list[str],
    scan_paths: tuple[str, ...] = SCAN_PATHS_DEFAULT,
    exclude: tuple[str, ...] = SCAN_EXCLUDE_DEFAULT,
) -> list[tuple[str, str]]:
    """掃 scan_paths、回 [(rel_path, term), ...]。

    含未替換 {{TEMPLATE}} placeholder 的檔整檔 skip（客戶未填、正常狀態）。
    forbidden_terms 為空 → 直接回 []（不掃）。
    """
    if not forbidden_terms:
        return []
    hits: list[tuple[str, str]] = []
    for pattern in scan_paths:
        for p in repo_root.glob(pattern):
            if not p.is_file():
                continue
            rel = str(p.relative_to(repo_root))
            if rel in exclude:
                continue
            content = p.read_text(encoding="utf-8")
            if PLACEHOLDER_RE.search(content):
                continue
            for term in forbidden_terms:
                if term in content:
                    hits.append((rel, term))
    return hits
