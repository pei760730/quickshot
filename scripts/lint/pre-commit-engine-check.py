#!/usr/bin/env python3
"""Pre-commit gate: engine-scope change must bump engine_version."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def parse_changed_files(base_ref: str = "origin/main", head_ref: str = "HEAD") -> list[str]:
    out = _run(["git", "diff", "--name-only", f"{base_ref}...{head_ref}"])
    return [x.strip() for x in out.splitlines() if x.strip()]


def _load_manifest(ref: str) -> dict:
    if ref == "HEAD":
        return json.loads(Path("engine-manifest.json").read_text(encoding="utf-8"))
    text = _run(["git", "show", f"{ref}:engine-manifest.json"])
    return json.loads(text)


def engine_scope_changed(files: list[str], blacklist: list[str]) -> bool:
    for path in files:
        if path == "engine-manifest.json":
            continue
        if any(path.startswith(prefix) for prefix in blacklist):
            continue
        return True
    return False


def run_gate(base_ref: str = "origin/main") -> tuple[bool, str]:
    changed = parse_changed_files(base_ref=base_ref, head_ref="HEAD")
    if not changed:
        return True, "no changes"
    head = _load_manifest("HEAD")
    blacklist = (head.get("_meta", {}).get("sync_blacklist") or [])
    if not engine_scope_changed(changed, blacklist):
        return True, "only blacklist paths changed"
    try:
        base = _load_manifest(base_ref)
    except Exception:
        base = {"_meta": {"engine_version": None}}
    hv = head.get("_meta", {}).get("engine_version")
    bv = base.get("_meta", {}).get("engine_version")
    if hv == bv:
        return False, "請 bump engine_version 或加 CHANGELOG engine 條目"
    return True, f"engine_version bumped: {bv} -> {hv}"


def main() -> None:
    ok, msg = run_gate()
    if not ok:
        print(f"❌ {msg}")
        raise SystemExit(1)
    print(f"✅ {msg}")


if __name__ == "__main__":
    main()
