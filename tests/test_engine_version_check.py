"""Tests for engine version CI guard logic (v4.65+ two-layer manifest)."""

import json
from pathlib import Path
from types import SimpleNamespace

from path_bootstrap import bootstrap_engine_test_sys_path

bootstrap_engine_test_sys_path()

import engine_version_check as evc  # noqa: E402


def _write_manifest_legacy(path: Path, version="4.13", files=None):
    """Legacy single-layer `files` schema (pre-v4.65)."""
    data = {"_meta": {"engine_version": version}, "files": files or {}}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _write_manifest_v2(path: Path, version, contract_files=None, internal_files=None, blacklist=None):
    """v4.65+ two-layer `contract_files` + `internal_files` schema."""
    meta = {"engine_version": version}
    if blacklist is not None:
        meta["sync_blacklist"] = blacklist
    data = {
        "_meta": meta,
        "contract_files": contract_files or {},
        "internal_files": internal_files or {},
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────
# Scope detection (v4.65+)
# ─────────────────────────────────────────────────────


def test_data_only_changes_skip(tmp_path, monkeypatch):
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# x", encoding="utf-8")
    _write_manifest_v2(tmp_path / "engine-manifest.json", version="4.65", contract_files={}, internal_files={"scripts/ops/video-ops.py": None})
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="data/kai/pipeline.json")])
    monkeypatch.setattr(evc, "_load_manifest_from_ref", lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {}, "internal_files": {}})
    assert evc.run_check("origin/main") == []


def test_internal_file_change_does_not_require_bump(tmp_path, monkeypatch):
    """v4.65+: changes to internal_files (scripts/** etc) no longer require bump."""
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# nothing", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.65",
        contract_files={},
        internal_files={"scripts/ops/video-ops.py": None},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="scripts/ops/video-ops.py")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {}, "internal_files": {"scripts/ops/video-ops.py": None}},
    )
    # Internal change + no bump + no CHANGELOG entry → still passes
    assert evc.run_check("origin/main") == []


def test_contract_file_change_requires_bump(tmp_path, monkeypatch):
    """v4.65+: changes to a contract_files entry require bump + CHANGELOG."""
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "pipeline-schema.md").write_text("> version: 1.1\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v4.65\n\n🔧 x\n", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.65",  # NOT bumped
        contract_files={"docs/contracts/pipeline-schema.md": "1.1"},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1"}},
    )
    errors = evc.run_check("origin/main")
    assert any("engine_version 未升版" in e for e in errors), errors


def test_contract_inline_version_must_match_manifest(tmp_path, monkeypatch):
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "pipeline-schema.md").write_text("> version: 1.2\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v4.66\n\n🔧 x\n", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.66",
        contract_files={"docs/contracts/pipeline-schema.md": "1.1"},  # stale version
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1"}},
    )
    errors = evc.run_check("origin/main")
    assert any("不一致" in e for e in errors), errors


def test_pass_when_contract_bumped_and_changelog_has_entry(tmp_path, monkeypatch):
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "pipeline-schema.md").write_text("> version: 1.2\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v4.66\n\n🔧 x\n", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.66",
        contract_files={"docs/contracts/pipeline-schema.md": "1.2"},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1"}},
    )
    assert evc.run_check("origin/main") == []




def test_contract_list_drift_without_manifest_change_is_ignored(tmp_path, monkeypatch):
    """Upstream contract_files drift alone should not force bump if PR didn't touch engine-manifest."""
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# x", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.65",
        contract_files={"docs/contracts/pipeline-schema.md": "1.1"},
    )
    monkeypatch.chdir(tmp_path)
    # PR only changes internal file; base/main may have different contract_files set.
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="scripts/ops/video-ops.py")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1", "CLAUDE.md": "4.13"}},
    )
    assert evc.run_check("origin/main") == []
def test_contract_list_change_also_triggers_bump(tmp_path, monkeypatch):
    """Adding/removing a contract_files entry is itself a contract change."""
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v4.65\n\n🔧 x\n", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.65",  # not bumped
        contract_files={"docs/contracts/pipeline-schema.md": "1.1", "CLAUDE.md": "4.13"},  # NEW entry
    )
    monkeypatch.chdir(tmp_path)
    # no file-level diff, just manifest
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="engine-manifest.json")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1"}},
    )
    errors = evc.run_check("origin/main")
    assert any("engine_version 未升版" in e for e in errors), errors


# ─────────────────────────────────────────────────────
# Backward compat with legacy `files` dict
# ─────────────────────────────────────────────────────


def test_legacy_manifest_files_still_parsed(tmp_path, monkeypatch):
    """Legacy `files` dict: non-null entries auto-classified as contract."""
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "pipeline-schema.md").write_text("> version: 1.1\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# nothing", encoding="utf-8")
    _write_manifest_legacy(
        tmp_path / "engine-manifest.json",
        version="4.55",  # not bumped
        files={"docs/contracts/pipeline-schema.md": "1.1"},  # treated as contract via fallback
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    monkeypatch.setattr(evc, "_load_manifest_from_ref", lambda ref: {"_meta": {"engine_version": "4.55"}, "files": {"docs/contracts/pipeline-schema.md": "1.1"}})
    errors = evc.run_check("origin/main")
    assert any("engine_version 未升版" in e for e in errors), errors


def test_legacy_manifest_null_entry_is_internal(tmp_path, monkeypatch):
    """Legacy `files` dict: null entries auto-classified as internal, no bump required."""
    (tmp_path / "scripts" / "ops").mkdir(parents=True)
    (tmp_path / "scripts" / "ops" / "video-ops.py").write_text("# x\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# nothing", encoding="utf-8")
    _write_manifest_legacy(
        tmp_path / "engine-manifest.json",
        version="4.55",
        files={"scripts/ops/video-ops.py": None},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="scripts/ops/video-ops.py")])
    monkeypatch.setattr(evc, "_load_manifest_from_ref", lambda ref: {"_meta": {"engine_version": "4.55"}, "files": {"scripts/ops/video-ops.py": None}})
    assert evc.run_check("origin/main") == []


# ─────────────────────────────────────────────────────
# Preserved behaviors
# ─────────────────────────────────────────────────────


def test_manifest_only_change_does_not_trigger_scope(tmp_path, monkeypatch):
    """engine-manifest.json 自身的純元資料變動（engine_version / last_updated）不觸發 scope check."""
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# x", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.65",
        contract_files={"docs/contracts/pipeline-schema.md": "1.1"},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="engine-manifest.json")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1"}},
    )
    assert evc.run_check("origin/main") == []


def test_blacklisted_contract_file_is_skipped(tmp_path, monkeypatch):
    """Blacklisted path with inline version should not trigger the inline-vs-manifest check even if listed."""
    (tmp_path / "dashboard" / "src").mkdir(parents=True)
    (tmp_path / "dashboard" / "src" / "ui-contract.md").write_text("> version: 1.6\n", encoding="utf-8")
    (tmp_path / "docs" / "contracts").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "pipeline-schema.md").write_text("> version: 1.2\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v4.66\n\n🔧 x\n", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.66",
        contract_files={
            "docs/contracts/pipeline-schema.md": "1.2",
            "dashboard/src/ui-contract.md": "1.5",  # blacklisted path — should be skipped
        },
        blacklist=["dashboard/**"],
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        evc, "parse_diff",
        lambda b, h: [
            SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md"),
            SimpleNamespace(status="M", path="dashboard/src/ui-contract.md"),
        ],
    )
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.2", "dashboard/src/ui-contract.md": "1.5"}},
    )
    assert evc.run_check("origin/main") == []


def test_changelog_version_bump_requires_engine_version_bump(tmp_path, monkeypatch):
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v4.66\n\n🔧 x\n", encoding="utf-8")
    _write_manifest_v2(
        tmp_path / "engine-manifest.json",
        version="4.65",
        contract_files={"docs/contracts/pipeline-schema.md": "1.1"},
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="docs/contracts/pipeline-schema.md")])
    monkeypatch.setattr(
        evc, "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "4.65"}, "contract_files": {"docs/contracts/pipeline-schema.md": "1.1"}},
    )
    monkeypatch.setattr(evc, "run_git", lambda args: "## v4.65\n\n🔧 y\n")
    errors = evc.run_check("origin/main")
    assert any("CHANGELOG 升 v4.66 但 _meta.engine_version 未動" in e for e in errors), errors


def test_factual_contract_change_checks_inline_but_does_not_require_bump(tmp_path, monkeypatch):
    """v5.95+: factual contracts can realign facts without engine bump/CHANGELOG."""
    (tmp_path / "README.md").write_text("> version: 8.10\n", encoding="utf-8"
    )
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# nothing", encoding="utf-8")
    data = {
        "_meta": {"engine_version": "5.95"},
        "semantic_contracts": {"docs/contracts/sync-protocol.md": "2.2"},
        "factual_contracts": {"README.md": "8.10"},
        "internal_files": {},
    }
    (tmp_path / "engine-manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="README.md")])
    monkeypatch.setattr(
        evc,
        "_load_manifest_from_ref",
        lambda ref: {
            "_meta": {"engine_version": "5.95"},
            "semantic_contracts": {"docs/contracts/sync-protocol.md": "2.2"},
            "factual_contracts": {"README.md": "8.9"},
        },
    )
    assert evc.run_check("origin/main") == []


def test_factual_contract_inline_mismatch_fails_without_bump_requirement(tmp_path, monkeypatch):
    """Factual entries still enforce own version alignment, but do not ask for bump."""
    (tmp_path / "README.md").write_text("> version: 8.10\n", encoding="utf-8")
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("# nothing", encoding="utf-8")
    data = {
        "_meta": {"engine_version": "5.95"},
        "semantic_contracts": {},
        "factual_contracts": {"README.md": "8.9"},
        "internal_files": {},
    }
    (tmp_path / "engine-manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="README.md")])
    monkeypatch.setattr(evc, "_load_manifest_from_ref", lambda ref: {"_meta": {"engine_version": "5.95"}, "factual_contracts": {"README.md": "8.9"}})
    errors = evc.run_check("origin/main")
    assert any("不一致" in e for e in errors), errors
    assert not any("engine_version 未升版" in e for e in errors), errors


def test_semantic_contract_list_change_triggers_bump_under_new_schema(tmp_path, monkeypatch):
    """Adding/removing semantic_contracts entries remains a semantic schema change."""
    (tmp_path / "07-changelog").mkdir(parents=True)
    (tmp_path / "07-changelog" / "CHANGELOG.md").write_text("## v5.95\n\n🔧 x\n", encoding="utf-8")
    data = {
        "_meta": {"engine_version": "5.94"},
        "semantic_contracts": {"docs/contracts/sync-protocol.md": "2.2"},
        "factual_contracts": {"README.md": "8.9"},
        "internal_files": {},
    }
    (tmp_path / "engine-manifest.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(evc, "parse_diff", lambda b, h: [SimpleNamespace(status="M", path="engine-manifest.json")])
    monkeypatch.setattr(
        evc,
        "_load_manifest_from_ref",
        lambda ref: {"_meta": {"engine_version": "5.94"}, "semantic_contracts": {}, "factual_contracts": {"README.md": "8.9"}},
    )
    errors = evc.run_check("origin/main")
    assert any("engine_version 未升版" in e for e in errors), errors
