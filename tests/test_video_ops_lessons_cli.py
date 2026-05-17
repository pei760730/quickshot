"""Tests for lessons CLI handler behaviors (v2.0 schema)."""

from lib.lessons import add_lesson, load_lessons
from path_bootstrap import load_video_ops_module


def test_lessons_stats_and_propose_hardening_v2(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}

    l1 = add_lesson(
        "kai",
        "manual",
        "cli-check",
        counter_pattern="do Y",
        evidence=["VID-001"],
    )
    l2 = add_lesson("kai", "manual", "no-cp", evidence=["VID-002"])

    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "lessons", "stats"])
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert "lessons stats" in out
    assert "soft: 2" in out
    assert "hardened: 0" in out

    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "lessons", "propose-hardening"])
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    # only l1 has counter_pattern
    assert l1 in out
    assert l2 not in out


def test_lessons_add_then_list(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}

    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py", "lessons", "add",
            "--pattern", "avoid fake quote",
            "--origin", "manual",
            "--stage", "soft",
            "--scope", "flow-operator,generation",
            "--evidence-vid", "VID-001",
            "--notes", "seed",
        ],
    )
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert "✅ lessons add" in out

    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "lessons", "list"])
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert "avoid fake quote" in out
    assert "soft" in out


def test_lessons_archive_cli(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"op_paths": {"operator": "kai"}}

    lesson_id = add_lesson("kai", "manual", "will-archive", evidence=["VID-001"])

    monkeypatch.setattr(
        video_ops.sys, "argv",
        ["video-ops.py", "lessons", "archive", lesson_id, "--reason", "obsolete"],
    )
    video_ops._cmd_lessons(ctx)
    out = capsys.readouterr().out
    assert "已 archive" in out

    rows = load_lessons("kai")
    assert rows[0]["stage"] == "archived"
    assert "obsolete" in rows[0].get("source_note", "")
