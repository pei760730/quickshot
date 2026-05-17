"""Tests for bump-engine tool."""

import json
from pathlib import Path
from types import SimpleNamespace

from path_bootstrap import bootstrap_engine_test_sys_path

bootstrap_engine_test_sys_path()

import bump_engine  # noqa: E402


def _seed_repo(tmp_path):
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# CHANGELOG\n\n---\n\n## v4.13（2026-04-18）\n\n🔧 old\n", encoding="utf-8")
    (tmp_path / "docs" / "contracts" / "pipeline-schema.md").write_text("> version: 1.2\n", encoding="utf-8")
    (tmp_path / "engine-manifest.json").write_text(json.dumps({
        "_meta": {
            "engine_version": "4.13",
            "last_updated": "2026-04-18",
            "client": {"name": "kai", "brand": "Red Tea Bus", "repo_type": "engine+client"},
        },
        "files": {"docs/contracts/pipeline-schema.md": "1.1"},
    }, ensure_ascii=False), encoding="utf-8")


def test_dry_run_is_idempotent(tmp_path, monkeypatch):
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bump_engine, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    plan1 = bump_engine.build_plan("origin/main")
    plan2 = bump_engine.build_plan("origin/main")
    assert plan1 == plan2
    manifest_text = (tmp_path / "engine-manifest.json").read_text(encoding="utf-8")
    assert '"engine_version": "4.13"' in manifest_text


def test_apply_updates_manifest_and_changelog(tmp_path, monkeypatch):
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bump_engine, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    plan = bump_engine.build_plan("origin/main")
    bump_engine.apply_plan(plan)

    manifest = json.loads((tmp_path / "engine-manifest.json").read_text(encoding="utf-8"))
    assert manifest["_meta"]["engine_version"] == "4.23"
    assert manifest["_meta"]["client"]["name"] == "kai"
    assert manifest["files"]["docs/contracts/pipeline-schema.md"] == "1.2"
    assert manifest["files"]["07-changelog/CHANGELOG.md"] == "4.23"

    changelog = (tmp_path / "07-changelog" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v4.23" in changelog
    assert "`docs/contracts/pipeline-schema.md`" in changelog
