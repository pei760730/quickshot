"""Tests for engine-manifest inline-version lint check."""

from pathlib import Path

from path_bootstrap import load_rules_lint_module


def test_engine_manifest_inline_mismatch_detected(tmp_path):
    rules_lint = load_rules_lint_module()
    repo_root = tmp_path
    f = repo_root / "docs" / "contracts" / "x.md"
    f.parent.mkdir(parents=True)
    f.write_text("> version: 1.1\n", encoding="utf-8")
    (repo_root / "engine-manifest.json").write_text(
        '{"_meta": {"engine_version": "1.0"}, "files": {"docs/contracts/x.md": "1.2"}}',
        encoding="utf-8",
    )
    rules_lint.REPO_ROOT = repo_root
    errors = []
    rules_lint.check_engine_manifest_inline_versions(errors)
    assert any(e["check"] == "engine_manifest_inline_mismatch" for e in errors)


def test_engine_manifest_inline_match_passes(tmp_path):
    rules_lint = load_rules_lint_module()
    repo_root = tmp_path
    f = repo_root / "docs" / "contracts" / "x.md"
    f.parent.mkdir(parents=True)
    f.write_text("> version: 1.2\n", encoding="utf-8")
    (repo_root / "engine-manifest.json").write_text(
        '{"_meta": {"engine_version": "1.0"}, "files": {"docs/contracts/x.md": "1.2"}}',
        encoding="utf-8",
    )
    rules_lint.REPO_ROOT = repo_root
    errors = []
    rules_lint.check_engine_manifest_inline_versions(errors)
    assert errors == []
