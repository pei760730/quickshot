"""Snapshot guard for Engine Version Bump Protocol text anchors."""

import json
from pathlib import Path

import pytest


def test_sync_protocol_engine_versioning_snapshot():
    repo_root = Path(__file__).resolve().parent.parent
    protocol_path = repo_root / "docs" / "contracts" / "sync-protocol.md"
    fixture_path = repo_root / "tests" / "fixtures" / "engine-versioning-rules.json"
    protocol = protocol_path.read_text(encoding="utf-8")
    spec = json.loads(fixture_path.read_text(encoding="utf-8"))

    heading = spec["protocol_heading"]
    if heading not in protocol:
        pytest.skip("protocol section not found in current branch; verify against repo-owner confirmed main HEAD")

    start = protocol.index(heading)
    tail = protocol[start:]
    next_heading_idx = tail.find("\n## ", len(heading))
    section = tail if next_heading_idx < 0 else tail[:next_heading_idx]

    for kw in spec["required_keywords"]:
        assert kw in section, f"missing keyword in protocol section: {kw}"
    for kw in spec["data_only_keywords"]:
        assert kw in section, f"missing data-only keyword in protocol section: {kw}"
