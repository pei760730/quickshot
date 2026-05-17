"""Tests for engine version utility base-ref resolution."""

from path_bootstrap import bootstrap_engine_test_sys_path

bootstrap_engine_test_sys_path()

import engine_version_utils as u  # noqa: E402


def test_resolve_base_ref_prefers_origin_main(monkeypatch):
    monkeypatch.setattr(u, "git_ref_exists", lambda ref: ref == "origin/main")
    base, assumed = u.resolve_base_ref("origin/main")
    assert base == "origin/main"
    assert assumed is None


def test_resolve_base_ref_falls_back_to_main(monkeypatch):
    monkeypatch.setattr(u, "git_ref_exists", lambda ref: ref in {"main"})
    monkeypatch.setattr(u, "run_git", lambda args: "abc123")
    base, assumed = u.resolve_base_ref("origin/main")
    assert base == "main"
    assert assumed == "abc123"
