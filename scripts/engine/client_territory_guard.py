#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client territory snapshot/verify/restore helpers for sync guard (L-0022 layer 2)."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from engine_version_utils import HARDCODED_CLIENT_TERRITORY, is_client_territory


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_client_territory(repo_root: Path) -> dict[str, str]:
    """掃 repo_root 下所有 is_client_territory 為真的檔、回 {rel_path: sha256}。"""
    snapshot: dict[str, str] = {}
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        if ".git" in p.parts:
            continue
        rel = str(p.relative_to(repo_root))
        if is_client_territory(rel, HARDCODED_CLIENT_TERRITORY):
            snapshot[rel] = _sha256(p)
    return snapshot


def verify_client_territory_unchanged(
    snapshot: dict[str, str], repo_root: Path
) -> tuple[bool, list[str]]:
    """回 (all_unchanged, list_of_changed_paths)。

    被刪 / sha 不符 / 新增（不在 snapshot 但是禁區檔）都算 changed。
    """
    changed: set[str] = set()

    for rel, expected in snapshot.items():
        p = repo_root / rel
        if not p.exists() or _sha256(p) != expected:
            changed.add(rel)

    current = snapshot_client_territory(repo_root)
    for rel in current:
        if rel not in snapshot:
            changed.add(rel)

    changed_list = sorted(changed)
    return (len(changed_list) == 0, changed_list)


def restore_client_territory(snapshot: dict[str, str], repo_root: Path) -> list[str]:
    """對變動禁區檔復原到 sync 前狀態。回實際 restore 的 paths。"""
    _, changed = verify_client_territory_unchanged(snapshot, repo_root)
    if not changed:
        return []

    tracked_or_missing = [rel for rel in changed if rel in snapshot]
    newly_added = [rel for rel in changed if rel not in snapshot]

    if tracked_or_missing:
        subprocess.run(
            ["git", "restore", "--source=HEAD", "--staged", "--worktree", "--", *tracked_or_missing],
            cwd=repo_root,
            check=True,
        )

    for rel in newly_added:
        p = repo_root / rel
        if p.exists():
            p.unlink()

    return changed
