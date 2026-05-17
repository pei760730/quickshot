from path_bootstrap import load_module_from_repo


def test_run_gate_pass_when_bumped(monkeypatch):
    mod = load_module_from_repo("scripts/lint/pre-commit-engine-check.py", "pre_commit_engine_check")
    monkeypatch.setattr(mod, "parse_changed_files", lambda **_kwargs: ["scripts/ops/video-ops.py"])
    monkeypatch.setattr(
        mod,
        "_load_manifest",
        lambda ref: {"_meta": {"engine_version": "4.48" if ref == "HEAD" else "4.47", "sync_blacklist": []}},
    )
    ok, msg = mod.run_gate()
    assert ok is True
    assert "bumped" in msg


def test_run_gate_fail_when_engine_changed_without_bump(monkeypatch):
    mod = load_module_from_repo("scripts/lint/pre-commit-engine-check.py", "pre_commit_engine_check")
    monkeypatch.setattr(mod, "parse_changed_files", lambda **_kwargs: ["scripts/ops/video-ops.py"])
    monkeypatch.setattr(
        mod,
        "_load_manifest",
        lambda ref: {"_meta": {"engine_version": "4.47", "sync_blacklist": []}},
    )
    ok, msg = mod.run_gate()
    assert ok is False
    assert "請 bump engine_version" in msg
