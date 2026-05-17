"""Tests for client territory snapshot/verify/restore guard."""

from pathlib import Path

from path_bootstrap import bootstrap_engine_test_sys_path

bootstrap_engine_test_sys_path()

import client_territory_guard as g  # noqa: E402


def test_snapshot_only_keeps_client_territory(tmp_path, monkeypatch):
    (tmp_path / "client").mkdir()
    (tmp_path / "client" / "keep.md").write_text("a", encoding="utf-8")
    (tmp_path / "engine").mkdir()
    (tmp_path / "engine" / "skip.md").write_text("b", encoding="utf-8")

    monkeypatch.setattr(g, "is_client_territory", lambda rel, *_: rel.startswith("client/"))

    snap = g.snapshot_client_territory(tmp_path)
    assert list(snap.keys()) == ["client/keep.md"]


def test_verify_detects_modified_deleted_and_added(tmp_path, monkeypatch):
    (tmp_path / "client").mkdir()
    a = tmp_path / "client" / "a.md"
    b = tmp_path / "client" / "b.md"
    a.write_text("old-a", encoding="utf-8")
    b.write_text("old-b", encoding="utf-8")

    monkeypatch.setattr(g, "is_client_territory", lambda rel, *_: rel.startswith("client/"))

    snap = g.snapshot_client_territory(tmp_path)

    a.write_text("new-a", encoding="utf-8")
    b.unlink()
    (tmp_path / "client" / "new.md").write_text("new", encoding="utf-8")

    ok, changed = g.verify_client_territory_unchanged(snap, tmp_path)
    assert ok is False
    assert changed == ["client/a.md", "client/b.md", "client/new.md"]


def test_restore_restores_tracked_and_deletes_new(tmp_path, monkeypatch):
    (tmp_path / "client").mkdir()
    tracked = tmp_path / "client" / "tracked.md"
    tracked.write_text("old", encoding="utf-8")

    snap = {"client/tracked.md": g._sha256(tracked)}
    tracked.write_text("new", encoding="utf-8")
    added = tmp_path / "client" / "added.md"
    added.write_text("added", encoding="utf-8")

    monkeypatch.setattr(
        g,
        "verify_client_territory_unchanged",
        lambda *_: (False, ["client/added.md", "client/tracked.md"]),
    )

    calls = []

    def _fake_run(cmd, cwd, check):
        calls.append((cmd, cwd, check))

    monkeypatch.setattr(g.subprocess, "run", _fake_run)

    restored = g.restore_client_territory(snap, tmp_path)

    assert restored == ["client/added.md", "client/tracked.md"]
    assert len(calls) == 1
    assert calls[0][0][:5] == ["git", "restore", "--source=HEAD", "--staged", "--worktree"]
    assert calls[0][0][-1] == "client/tracked.md"
    assert added.exists() is False


def test_is_client_territory_supports_negation():
    assert g.is_client_territory("data/customer/file.md", ["data/**", "!data/template/**"]) is True
    assert g.is_client_territory("data/template/file.md", ["data/**", "!data/template/**"]) is False
