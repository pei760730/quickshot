"""Trace-required coverage for video-ops quick-add and transition paths."""

import json

import pytest
from path_bootstrap import load_video_ops_module


TRACE = {
    "skill_used": "flow-operator",
    "skill_version": "1.50",
    "generated_at": "2026-04-25",
    "title_type": "T3",
    "hook_type": "B2",
    "version_chosen": "D",
}


def _ctx(video_ops):
    data = video_ops.load_tracking()
    data["_meta"].setdefault("statuses", {})["video"] = ["待拍", "剪輯中", "已上線"]
    data["_meta"]["trace_required_statuses"] = ["剪輯中", "已上線"]
    data["_meta"]["valid_title_types"] = ["T1", "T2", "T3", "T4", "T5"]
    data["_meta"]["valid_hook_types"] = ["D1", "D2", "D3", "B1", "B2", "B3"]
    return {"data": data, "op_paths": {"operator": "kai", "vid_prefix": "VID"}}


def _quick_add_argv(*extra):
    return [
        "video-ops.py",
        "quick-add",
        "--topic",
        "測試主題",
        "--tag",
        "測試標籤",
        "--title",
        "測試標題",
        *extra,
    ]


def test_quick_add_required_status_no_trace_exit_1(patch_paths, monkeypatch, capsys):
    video_ops = load_video_ops_module()
    ctx = _ctx(video_ops)
    monkeypatch.setattr(video_ops.sys, "argv", _quick_add_argv("--status", "剪輯中"))

    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_quick_add(ctx)

    assert exc.value.code == 1
    assert "需提供 generation_trace" in capsys.readouterr().out
    assert ctx["data"]["videos"] == []


def test_quick_add_required_status_with_trace_ok(patch_paths, monkeypatch):
    video_ops = load_video_ops_module()
    ctx = _ctx(video_ops)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        _quick_add_argv("--status", "剪輯中", "--trace", json.dumps(TRACE, ensure_ascii=False)),
    )

    video_ops._cmd_quick_add(ctx)

    assert ctx["data"]["videos"][0]["vid"] == "VID-001"
    assert ctx["data"]["videos"][0]["status"] == "剪輯中"
    assert ctx["data"]["videos"][0]["generation_trace"]["version_chosen"] == "D"


def test_quick_add_allow_missing_trace_writes_backfill(patch_paths, monkeypatch):
    video_ops = load_video_ops_module()
    ctx = _ctx(video_ops)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        _quick_add_argv("--status", "已上線", "--allow-missing-trace"),
    )

    video_ops._cmd_quick_add(ctx)

    trace = ctx["data"]["videos"][0]["generation_trace"]
    assert trace["skill_used"] == "manual_backfill"
    assert trace["reason"] == "quick-add bypass"


def test_transition_to_required_status_no_trace_exit_1(patch_paths, monkeypatch, capsys):
    video_ops = load_video_ops_module()
    ctx = _ctx(video_ops)
    monkeypatch.setattr(video_ops.sys, "argv", _quick_add_argv("--status", "待拍"))
    video_ops._cmd_quick_add(ctx)

    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "transition", "VID-001", "剪輯中"])
    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_transition(ctx)

    assert exc.value.code == 1
    assert "需提供 generation_trace" in capsys.readouterr().out
    assert "generation_trace" not in ctx["data"]["videos"][0]
