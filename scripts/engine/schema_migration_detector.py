"""Schema migration detector helpers for sync-isolation flow."""

from __future__ import annotations

from pathlib import Path

SCHEMA_PATH_PREFIXES: tuple[str, ...] = (
    "docs/contracts/",
    "data/template/",
)
SCHEMA_FILE_SUFFIXES: tuple[str, ...] = (
    "-schema.md",
    "schema.json",
)


def is_schema_related_path(rel_path: str) -> bool:
    """Return True when a changed path belongs to schema/migration surface."""
    if rel_path.startswith(SCHEMA_PATH_PREFIXES):
        return True
    return rel_path.endswith(SCHEMA_FILE_SUFFIXES)


def detect_schema_migration(changed_paths: list[str]) -> bool:
    """Return True when changed_paths contains at least one schema-related file."""
    return any(is_schema_related_path(p) for p in changed_paths)


def detect_schema_migration_in_repo(repo_root: Path, changed_paths: list[str]) -> list[str]:
    """Return existing schema-related files from changed_paths (repo-relative)."""
    hits: list[str] = []
    for rel in changed_paths:
        if is_schema_related_path(rel) and (repo_root / rel).exists():
            hits.append(rel)
    return hits


import re

SCHEMA_MIGRATION_MARKER_RE = re.compile(
    r"^\s*🚨\s*schema[\-\s]*migration\b", re.IGNORECASE
)


def detect_schema_migration_marker(changelog_text: str) -> list[str]:
    """從 CHANGELOG 文本（或 diff）擷取所有含 🚨 schema-migration 的行。

    對應 L-0022 第四層防護：客戶端 /sync 偵測到此標記 → 強制停下、
    不 auto-merge、要客戶手動跑 migration。

    回 trimmed line list、空 list = 沒偵測到。
    """
    hits: list[str] = []
    for line in changelog_text.splitlines():
        if SCHEMA_MIGRATION_MARKER_RE.search(line):
            hits.append(line.strip())
    return hits


def has_schema_migration_marker(changelog_text: str) -> bool:
    """便利 wrapper：偵測到任一行 🚨 schema-migration → True。"""
    return bool(detect_schema_migration_marker(changelog_text))
