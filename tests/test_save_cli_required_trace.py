import json

import pytest
from conftest import make_video
from path_bootstrap import load_video_ops_module


TRACE = json.dumps({
    "skill_used": "generation",
    "skill_version": "4.7",
    "generated_at": "2026-05-07",
    "title_type": "T3",
    "hook_type": "B2",
    "version_chosen": "B",
    "patterns_injected": ["open-loop"],
    "risk_patterns_avoided": ["AI口吻"],
    "persona_deviation_score": 1,
    "verifier_prediction": "high",
    "mode": "dual-track",
    "title_candidates": ["候選 A", "候選 B"],
}, ensure_ascii=False)


def _pipeline(video):
    item = {"idea_id": "IDEA-001", "topic": video["topic"]}
    item.update(video)
    return {
        "_meta": {
            "valid_title_types": ["T3"],
            "valid_hook_types": ["B2"],
            "valid_versions": ["B2"],
            "valid_verifier_predictions": ["high"],
        },
        "items": [item],
        "videos": [item.copy()],
    }


def _argv(*extra):
    return [
        "video-ops.py", "save", "VID-001",
        "--script-path", "03-production-line/02-ready-to-shoot/test.md",
        "--title-type", "T3",
        "--hook-type", "B2",
        "--version", "B2",
        "--verifier-prediction", "high",
        *extra,
    ]


def test_save_without_trace_exits_1_with_contract_error(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": _pipeline(make_video(vid="VID-001", status="待拍", topic="紅茶測試")), "op_paths": {}}
    monkeypatch.setattr(video_ops.sys, "argv", _argv())

    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_save(ctx)

    assert exc.value.code == 1
    assert "trace 必填、見 generation SKILL.md §Output Contract" in capsys.readouterr().out


def test_save_success_prints_structured_stdout_without_trace_json(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": _pipeline(make_video(vid="VID-001", status="待拍", topic="紅茶測試", title="封面標題")), "op_paths": {}}
    monkeypatch.setattr(video_ops.sys, "argv", _argv("--trace", TRACE))

    video_ops._cmd_save(ctx)

    out = capsys.readouterr().out
    assert "VID：VID-001" in out
    assert "主題：紅茶測試" in out
    assert "skill：generation@4.7" in out
    assert "mode：dual-track" in out
    assert "hook_type：B2" in out
    assert "title 候選：候選 A / 候選 B" in out
    assert "品質快照：patterns=1 / risk_avoided=1 / persona_deviation=1.0 / verifier_prediction=high" in out
    assert '"skill_used"' not in out


def test_save_quiet_suppresses_success_stdout(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": _pipeline(make_video(vid="VID-001", status="待拍", topic="紅茶測試")), "op_paths": {}}
    monkeypatch.setattr(video_ops.sys, "argv", _argv("--trace", TRACE, "--quiet"))

    video_ops._cmd_save(ctx)

    assert capsys.readouterr().out == ""
