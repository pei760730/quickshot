"""Engine lag detector — read local and remote engine versions, compare."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


FETCH_TIMEOUT_SECONDS = 3
SHOW_TIMEOUT_SECONDS = 3
SCHEMA_MIGRATION_MARKER = "🚨 schema-migration"


def fetch_engine_main(repo_root: Path, timeout: int = FETCH_TIMEOUT_SECONDS) -> bool:
    """Fetch engine/main; timeout or missing remote returns False without raising."""
    try:
        result = subprocess.run(
            ["git", "fetch", "engine", "main", "-q"],
            cwd=repo_root,
            timeout=timeout,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def read_local_engine_version(repo_root: Path) -> str | None:
    """Read _meta.engine_version from engine-manifest.json; return None if unavailable."""
    manifest = repo_root / "engine-manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("_meta", {}).get("engine_version")
    except (json.JSONDecodeError, OSError):
        return None


def read_remote_engine_version(repo_root: Path) -> str | None:
    """Read _meta.engine_version from engine/main:engine-manifest.json."""
    try:
        result = subprocess.run(
            ["git", "show", "engine/main:engine-manifest.json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=SHOW_TIMEOUT_SECONDS,
        )
        data = json.loads(result.stdout)
        return data.get("_meta", {}).get("engine_version")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _version_marker(version: str | None) -> str | None:
    if not version:
        return None
    return f"## v{version.lstrip('v')}"


def count_remote_schema_migrations(repo_root: Path, local: str, remote: str) -> int:
    """Count remote changelog schema-migration markers between local and remote.

    The changelog is newest-first. When both version headings are present, this counts
    entries after the remote heading through entries before the local heading. If the
    local version is too old to be present, count all visible remote changelog markers.
    Any git/show failure returns 0 so session-start checks remain silent and safe.
    """
    try:
        result = subprocess.run(
            ["git", "show", "engine/main:07-changelog/CHANGELOG.md"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=SHOW_TIMEOUT_SECONDS,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return 0

    changelog = result.stdout
    local_marker = _version_marker(local)
    remote_marker = _version_marker(remote)

    start = changelog.find(remote_marker) if remote_marker else -1
    end = changelog.find(local_marker) if local_marker else -1

    if start == -1:
        start = 0
    if end == -1 or end <= start:
        scope = changelog[start:]
    else:
        scope = changelog[start:end]
    return scope.count(SCHEMA_MIGRATION_MARKER)


def compare_versions(local: str, remote: str) -> str:
    """Compare semver-ish strings. Return behind, current, ahead, or unknown."""
    if not local or not remote:
        return "unknown"
    try:
        local_parts = tuple(int(part) for part in local.lstrip("v").split("."))
        remote_parts = tuple(int(part) for part in remote.lstrip("v").split("."))
    except (ValueError, AttributeError):
        return "unknown"

    if local_parts < remote_parts:
        return "behind"
    if local_parts > remote_parts:
        return "ahead"
    return "current"
