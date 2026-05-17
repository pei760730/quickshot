#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Engine version bump helper."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from engine_version_utils import (
    bump_version,
    has_inline_version,
    is_blacklisted,
    parse_diff,
    parse_manifest_files,
    read_json,
    resolve_base_ref,
)


BREAKING_HINTS = (
    "docs/contracts/",
    "scripts/ops/lib/pipeline.py",
    "scripts/ops/lib/validate.py",
)


def _is_breaking(changed_paths: list[str]) -> bool:
    return any(any(p.startswith(h) for h in BREAKING_HINTS) for p in changed_paths)


def _engine_changed_paths(diff_items, known_manifest_paths: set[str]) -> list[str]:
    result = []
    for item in diff_items:
        if is_blacklisted(item.path):
            continue
        if item.path in known_manifest_paths or item.status.startswith(("A", "D", "M")):
            result.append(item.path)
    return sorted(set(result))


def _build_changelog_stub(version: str, changed_paths: list[str]) -> str:
    today = date.today().isoformat()
    lines = [
        f"## v{version}（{today}）",
        "",
        "**主題：待補（請 Claude 填寫）**",
        "",
        "### 🔧 引擎變更（待補敘述）",
        "",
    ]
    for p in changed_paths:
        lines.append(f"- `{p}`")
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def _prepend_changelog(changelog_path: Path, stub: str):
    text = changelog_path.read_text(encoding="utf-8")
    marker = "---\n"
    idx = text.find(marker)
    if idx < 0:
        changelog_path.write_text(stub + "\n" + text, encoding="utf-8")
        return
    insert_at = idx + len(marker) + 1
    updated = text[:insert_at] + "\n" + stub + text[insert_at:]
    changelog_path.write_text(updated, encoding="utf-8")


def build_plan(base_ref: str = "origin/main") -> dict:
    manifest_path = Path("engine-manifest.json")
    changelog_path = Path("07-changelog/CHANGELOG.md")
    manifest = read_json(manifest_path)
    files = parse_manifest_files(manifest)
    diff_items = parse_diff(base_ref, "HEAD")
    engine_paths = _engine_changed_paths(diff_items, set(files.keys()))
    if not engine_paths:
        return {"changed_engine_files": [], "noop": True}

    old_engine_v = manifest.get("_meta", {}).get("engine_version", "0.00")
    new_engine_v = bump_version(old_engine_v, breaking=_is_breaking(engine_paths))

    file_updates = {}
    for item in diff_items:
        p = item.path
        if is_blacklisted(p):
            continue
        if item.status.startswith("D"):
            file_updates[p] = {"action": "delete", "version": None}
            continue
        if p not in engine_paths:
            continue
        inline = has_inline_version(Path(p))
        file_updates[p] = {"action": "upsert", "version": inline}

    # bump tool 會自動 prepend CHANGELOG；即使本次 diff 沒動到 CHANGELOG，
    # 也必須同步更新 manifest.files 的版本映射，避免舊版本卡住。
    file_updates[str(changelog_path)] = {"action": "upsert", "version": new_engine_v}

    return {
        "noop": False,
        "old_engine_version": old_engine_v,
        "new_engine_version": new_engine_v,
        "file_updates": file_updates,
        "changed_engine_files": engine_paths,
        "changelog_stub": _build_changelog_stub(new_engine_v, engine_paths),
        "manifest_path": str(manifest_path),
        "changelog_path": str(changelog_path),
    }


def apply_plan(plan: dict):
    if plan.get("noop"):
        return
    manifest_path = Path(plan["manifest_path"])
    changelog_path = Path(plan["changelog_path"])
    manifest = read_json(manifest_path)
    files = parse_manifest_files(manifest)

    manifest["_meta"]["engine_version"] = plan["new_engine_version"]
    manifest["_meta"]["last_updated"] = date.today().isoformat()
    modern_layers = ["semantic_contracts", "factual_contracts", "internal_files"]
    is_modern = any(isinstance(manifest.get(layer), dict) for layer in modern_layers)
    if is_modern:
        for layer in modern_layers:
            if not isinstance(manifest.get(layer), dict):
                manifest[layer] = {}

        def upsert_modern(path: str, version):
            for layer in modern_layers:
                if path in manifest[layer]:
                    manifest[layer][path] = version
                    return
            manifest["internal_files"][path] = version

        for p, op in plan["file_updates"].items():
            if op["action"] == "delete":
                for layer in modern_layers:
                    manifest[layer].pop(p, None)
            else:
                upsert_modern(p, op["version"])
    else:
        for p, op in plan["file_updates"].items():
            if op["action"] == "delete":
                files.pop(p, None)
            else:
                files[p] = op["version"]
        manifest["files"] = files
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _prepend_changelog(changelog_path, plan["changelog_stub"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    base_ref, assumed_sha = resolve_base_ref(args.base)
    plan = build_plan(base_ref)
    plan["base_ref"] = base_ref
    if assumed_sha is not None:
        plan["assumed_main_sha"] = assumed_sha
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.apply:
        apply_plan(plan)
        print("✅ bump applied")


if __name__ == "__main__":
    main()
