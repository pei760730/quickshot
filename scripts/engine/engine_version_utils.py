#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Engine version protocol helpers.

v4.24 重構：引擎同步從 opt-in（`_meta.files` 清單）改為 opt-out（`_meta.sync_blacklist` 路徑規則）。
- `is_blacklisted(path, blacklist=None)` 是新 API：檢查 path 是否符合 blacklist glob，支援 `!rule` negation。
- `is_data_only_path` 保留為 backward-compat wrapper，底層仍走 blacklist 判斷。
- `_DEFAULT_BLACKLIST` 作為 manifest 讀不到時的 fallback（舊 DATA_ONLY_PATTERNS 語意）。
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path


# Fallback blacklist（當 engine-manifest 讀不到 sync_blacklist 時用）。
# 語意對齊舊 DATA_ONLY_PATTERNS + 加 Kai 特有路徑 + negation 保護通用協作憲章。
_DEFAULT_BLACKLIST = (
    "data/**",
    "!data/template/**",
    "01-data-brain/brand*.md",
    "01-data-brain/cases.md",
    "01-data-brain/transcripts/**",
    "03-production-line/**",
    "00-control-center/todo/**",
    "dashboard/**",
    "docs/contracts/*-collaboration.md",
    "!docs/contracts/agent-collaboration.md",
    "CLAUDE.local.md",
)


def load_sync_blacklist(manifest_path: Path | str | None = None) -> tuple[str, ...]:
    """從 engine-manifest.json 讀 `_meta.sync_blacklist`；讀不到回 _DEFAULT_BLACKLIST。

    manifest_path=None 時從 repo root（以本檔推算）自動解析。
    """
    if manifest_path is None:
        manifest_path = Path(__file__).resolve().parent.parent.parent / "engine-manifest.json"
    try:
        data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        bl = data.get("_meta", {}).get("sync_blacklist")
        if isinstance(bl, list) and bl:
            return tuple(bl)
    except Exception:
        pass
    return _DEFAULT_BLACKLIST


def is_blacklisted(path: str, blacklist: tuple[str, ...] | list[str] | None = None) -> bool:
    """檢查 path 是否符合 blacklist 規則。

    Glob rules（fnmatch）：
    - `data/**` → match `data/*` 下任何深度
    - `!data/template/**` → 明確排除（higher priority than blacklist）
    - `docs/contracts/*-collaboration.md` → 特定檔名 pattern

    Negation（`!rule`）優先於普通 rule：若 path match negation → 回 False（算引擎、不 blacklist）。
    """
    # None 或空容器 → 回退讀 manifest（避免呼叫端誤傳 `()` 導致所有路徑被當 engine）
    if not blacklist:
        blacklist = load_sync_blacklist()

    # Pass 1: 先看 negation
    for rule in blacklist:
        if rule.startswith("!") and fnmatchcase(path, rule[1:]):
            return False

    # Pass 2: 再看 blacklist
    for rule in blacklist:
        if not rule.startswith("!") and fnmatchcase(path, rule):
            return True

    return False


# Backward-compat alias（既有 caller 不用改）
DATA_ONLY_PATTERNS = ()  # 棄用、留空。呼叫者應改用 is_blacklisted


def is_data_only_path(path: str) -> bool:
    """[DEPRECATED] Use is_blacklisted(path) instead.

    Backward-compat wrapper。語意從舊「data-only」擴大為「blacklisted」。
    """
    return is_blacklisted(path)


# v4.66 L-0022 layer 2: client territory helpers（for sync snapshot guard）
HARDCODED_CLIENT_TERRITORY = tuple(_DEFAULT_BLACKLIST)


def is_client_territory(
    path: str, rules: tuple[str, ...] | list[str] | None = None
) -> bool:
    """Return whether a path belongs to client territory.

    By default this uses HARDCODED_CLIENT_TERRITORY, and supports `!rule`
    negation semantics the same as `is_blacklisted`.
    """
    if rules is None:
        rules = HARDCODED_CLIENT_TERRITORY
    return is_blacklisted(path, rules)


@dataclass
class DiffItem:
    status: str
    path: str


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def git_ref_exists(ref: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def resolve_base_ref(preferred: str = "origin/main") -> tuple[str, str | None]:
    """Resolve a usable diff base ref.

    Returns (base_ref, assumed_sha).
    - assumed_sha is None when preferred ref exists.
    - assumed_sha is set when falling back to local refs.
    """
    if git_ref_exists(preferred):
        return preferred, None

    for candidate in ("main", "master"):
        if git_ref_exists(candidate):
            sha = run_git(["rev-parse", "--short", candidate])
            return candidate, sha

    # last resort: previous commit from current HEAD
    if git_ref_exists("HEAD~1"):
        sha = run_git(["rev-parse", "--short", "HEAD~1"])
        return "HEAD~1", sha

    sha = run_git(["rev-parse", "--short", "HEAD"])
    return "HEAD", sha


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_legacy_files(manifest: dict) -> dict:
    """Return legacy single-layer manifest entries, if present."""
    if isinstance(manifest.get("files"), dict):
        return manifest["files"]
    meta_files = manifest.get("_meta", {}).get("files", {})
    if isinstance(meta_files, dict):
        return meta_files
    if isinstance(meta_files, list):
        return {p: None for p in meta_files if isinstance(p, str)}
    return {}


def parse_semantic_contracts(manifest: dict) -> dict:
    """Return files whose changes require engine bump + CHANGELOG.

    v5.95 replaces the old `contract_files` block with `semantic_contracts`
    （rules / APIs / skills / contracts that can change customer Claude behavior）.
    Legacy manifests are still readable as git diff bases: `contract_files` and
    non-null legacy `files` entries are treated as semantic.
    """
    semantic = manifest.get("semantic_contracts")
    if isinstance(semantic, dict):
        return semantic

    legacy_contract = manifest.get("contract_files")
    if isinstance(legacy_contract, dict):
        return legacy_contract

    legacy = _parse_legacy_files(manifest)
    return {k: v for k, v in legacy.items() if v is not None}


def parse_factual_contracts(manifest: dict) -> dict:
    """Return fact/history/doc files tracked for version consistency only.

    Changes to factual contracts do not require engine bump or CHANGELOG, but
    their inline `> version:` header must still match the manifest entry.
    """
    factual = manifest.get("factual_contracts")
    if isinstance(factual, dict):
        return factual
    return {}


def parse_contract_files(manifest: dict) -> dict:
    """Backward-compatible alias for semantic contracts.

    New code should call `parse_semantic_contracts()` or
    `parse_factual_contracts()` explicitly.
    """
    return parse_semantic_contracts(manifest)


def parse_manifest_files(manifest: dict) -> dict:
    """Return all manifest-tracked files across semantic/factual/internal layers."""
    semantic = manifest.get("semantic_contracts")
    factual = manifest.get("factual_contracts")
    internal = manifest.get("internal_files")
    legacy_contract = manifest.get("contract_files")
    if any(isinstance(block, dict) for block in (semantic, factual, internal, legacy_contract)):
        combined = {}
        for block in (legacy_contract, semantic, factual, internal):
            if isinstance(block, dict):
                combined.update(block)
        return combined

    return _parse_legacy_files(manifest)


def has_inline_version(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines()[:20]:
        m = re.match(r"^\s*>\s*version:\s*([0-9]+\.[0-9]+)\b", line)
        if m:
            return m.group(1)
    return None


def parse_diff(base_ref: str, head_ref: str = "HEAD") -> list[DiffItem]:
    out = run_git(["diff", "--name-status", f"{base_ref}...{head_ref}"])
    if not out:
        return []
    items: list[DiffItem] = []
    for raw in out.splitlines():
        cols = raw.split("\t")
        if not cols:
            continue
        status = cols[0]
        path = cols[-1]
        items.append(DiffItem(status=status, path=path))
    return items


def parse_version(v: str) -> tuple[int, int]:
    a, b = v.split(".")
    return int(a), int(b)


def format_version(major: int, minor: int) -> str:
    return f"{major}.{minor:02d}"


def bump_version(version: str, breaking: bool = False) -> str:
    major, minor = parse_version(version)
    if breaking:
        minor += 10
        if minor >= 100:
            major += minor // 100
            minor = minor % 100
    else:
        minor += 1
        if minor >= 100:
            major += minor // 100
            minor = minor % 100
    return format_version(major, minor)


def changelog_has_engine_entry(changelog_text: str, version: str) -> bool:
    heading = f"## v{version}"
    start = changelog_text.find(heading)
    if start < 0:
        return False
    next_idx = changelog_text.find("\n## v", start + len(heading))
    section = changelog_text[start: next_idx if next_idx >= 0 else len(changelog_text)]
    return "🔧" in section
