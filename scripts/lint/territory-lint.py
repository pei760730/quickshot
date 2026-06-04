#!/usr/bin/env python3
"""Fail agent PRs that modify files outside their configured territory."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".github" / "agent-territory.json"


def normalize_path(path: str) -> str:
    """Normalize paths for cross-platform glob matching."""
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _segment_matches(path_segment: str, pattern_segment: str) -> bool:
    regex = ""
    for char in pattern_segment:
        if char == "*":
            regex += "[^/]*"
        else:
            regex += re.escape(char)
    return re.fullmatch(regex, path_segment) is not None


def path_matches(path: str, pattern: str) -> bool:
    """Match a normalized path against a glob with ``*`` and ``**`` support."""
    path_parts = tuple(part for part in normalize_path(path).split("/") if part)
    pattern_parts = tuple(part for part in normalize_path(pattern).split("/") if part)

    @lru_cache(maxsize=None)
    def match(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)

        pattern_part = pattern_parts[pattern_index]
        if pattern_part == "**":
            return match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )

        return (
            path_index < len(path_parts)
            and _segment_matches(path_parts[path_index], pattern_part)
            and match(path_index + 1, pattern_index + 1)
        )

    return match(0, 0)


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def current_branch() -> str:
    return os.environ.get("GITHUB_HEAD_REF") or run_git(["rev-parse", "--abbrev-ref", "HEAD"])


def changed_files(base: str) -> list[str]:
    output = run_git(["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"])
    return [line for line in output.splitlines() if line]


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def select_territory(config: dict, branch: str) -> tuple[str, dict] | tuple[None, None]:
    for name, territory in config.get("territories", {}).items():
        prefixes = territory.get("branch_prefixes", [])
        if any(branch.startswith(prefix) for prefix in prefixes):
            return name, territory
    return None, None


def violation_reason(path: str, territory: dict) -> str | None:
    allow_patterns = territory.get("allow", [])
    deny_patterns = territory.get("deny", [])

    for pattern in deny_patterns:
        if path_matches(path, pattern):
            return f"命中deny:{pattern}"

    if not any(path_matches(path, pattern) for pattern in allow_patterns):
        return "allow未命中"

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint agent branch path territory.")
    parser.add_argument("--base", default="origin/main", help="Base ref for git diff.")
    parser.add_argument("--branch", help="Branch name. Defaults to GITHUB_HEAD_REF or current branch.")
    parser.add_argument("--files", nargs="*", help="Changed files to lint without running git.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    branch = args.branch or current_branch()
    config = load_config()
    territory_name, territory = select_territory(config, branch)

    if territory_name is None or territory is None:
        print(f"✅ territory-lint skipped: branch '{branch}' has no matching territory")
        return 0

    files = args.files if args.files is not None else changed_files(args.base)
    violations = []
    for file_path in files:
        normalized = normalize_path(file_path)
        reason = violation_reason(normalized, territory)
        if reason is not None:
            violations.append((normalized, reason))

    if violations:
        print(f"❌ territory-lint failed for branch '{branch}' (territory={territory_name})")
        for file_path, reason in violations:
            print(f"{file_path} 越界（territory={territory_name}，原因={reason}）")
        return 1

    print(f"✅ territory-lint passed for branch '{branch}' (territory={territory_name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
