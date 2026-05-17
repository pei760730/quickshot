#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI guard for Engine Version Bump Protocol.

v5.95+ separates manifest contract tracking into two layers:
- semantic_contracts: rules / APIs / skill contracts; changes require engine bump + CHANGELOG.
- factual_contracts: fact/history/descriptive docs; changes only require inline-version alignment.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from engine_version_utils import (
    changelog_has_engine_entry,
    resolve_base_ref,
    has_inline_version,
    is_blacklisted,
    parse_diff,
    parse_factual_contracts,
    parse_semantic_contracts,
    run_git,
)


def _load_manifest_from_ref(ref: str) -> dict:
    text = run_git(["show", f"{ref}:engine-manifest.json"])
    return json.loads(text)


def _semantic_scope_changed(diff_items, semantic_paths: set[str]) -> bool:
    """Return whether file-level diff touches semantic contracts."""
    for item in diff_items:
        if item.path == "engine-manifest.json":
            continue
        if item.path in semantic_paths:
            return True
    return False


def _semantic_contract_list_changed(base_manifest: dict, head_manifest: dict) -> bool:
    """Adding/removing semantic_contracts entries changes behavior and requires bump."""
    base_keys = set(parse_semantic_contracts(base_manifest).keys())
    head_keys = set(parse_semantic_contracts(head_manifest).keys())
    return base_keys != head_keys


def _latest_changelog_version(text: str) -> str | None:
    match = re.search(r"^## v(\d+\.\d+)\b", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def _inline_version_errors(diff_items, manifest_entries: dict, blacklist) -> list[str]:
    """Validate changed semantic+factual files with inline versions against manifest."""
    errors: list[str] = []
    tracked_paths = set(manifest_entries.keys())
    for item in diff_items:
        if item.status.startswith("D"):
            continue
        if item.path not in tracked_paths:
            continue
        if is_blacklisted(item.path, blacklist):
            continue
        path = Path(item.path)
        inline = has_inline_version(path)
        if inline is None:
            continue
        manifest_v = manifest_entries.get(item.path)
        if manifest_v is None:
            errors.append(f"{item.path} 有 inline version={inline} 但 manifest 未記錄版本")
            continue
        if str(manifest_v) != inline:
            errors.append(f"{item.path} inline version={inline} 與 manifest={manifest_v} 不一致")
    return errors


def run_check(base_ref: str, head_ref: str = "HEAD") -> list[str]:
    errors: list[str] = []
    diff_items = parse_diff(base_ref, head_ref)
    head_manifest = json.loads(Path("engine-manifest.json").read_text(encoding="utf-8"))
    base_manifest = _load_manifest_from_ref(base_ref)
    head_semantic = parse_semantic_contracts(head_manifest)
    head_factual = parse_factual_contracts(head_manifest)
    blacklist = head_manifest.get("_meta", {}).get("sync_blacklist") or ()

    versioned_contracts = {}
    versioned_contracts.update(head_semantic)
    versioned_contracts.update(head_factual)
    errors.extend(_inline_version_errors(diff_items, versioned_contracts, blacklist))

    semantic_paths = set(head_semantic.keys())

    # Only semantic changes require bump. Manifest list diffs count only when the PR
    # itself touched engine-manifest, to avoid stale branches being flagged for main drift.
    manifest_changed = any(item.path == "engine-manifest.json" for item in diff_items)
    list_changed = manifest_changed and _semantic_contract_list_changed(base_manifest, head_manifest)
    semantic_changed = _semantic_scope_changed(diff_items, semantic_paths) or list_changed
    if not semantic_changed:
        return errors

    head_v = head_manifest.get("_meta", {}).get("engine_version")
    base_v = base_manifest.get("_meta", {}).get("engine_version")
    if head_v == base_v:
        errors.append("engine_version 未升版（_meta.engine_version 與 origin/main 相同；semantic_contracts scope 有變動）")

    changelog = Path("07-changelog/CHANGELOG.md").read_text(encoding="utf-8")
    if not changelog_has_engine_entry(changelog, str(head_v)):
        errors.append(f"CHANGELOG 缺少 v{head_v} 的 🔧 引擎條目")
    try:
        base_changelog = run_git(["show", f"{base_ref}:07-changelog/CHANGELOG.md"])
    except subprocess.CalledProcessError:
        base_changelog = changelog
    base_latest = _latest_changelog_version(base_changelog)
    head_latest = _latest_changelog_version(changelog)
    if base_latest != head_latest and head_v == base_v:
        errors.append(f"CHANGELOG 升 v{head_latest} 但 _meta.engine_version 未動")

    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args()
    base_ref, assumed_sha = resolve_base_ref(args.base)
    if assumed_sha is not None:
        print(f"⚠️ base ref '{args.base}' unavailable; based on assumed main @ {assumed_sha} ({base_ref})")
    errors = run_check(base_ref, args.head)
    if errors:
        for e in errors:
            print(f"❌ {e}")
        raise SystemExit(1)
    print("✅ engine-version-check passed")


if __name__ == "__main__":
    main()
