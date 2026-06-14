from conftest import make_video
from path_bootstrap import load_video_ops_module


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


def test_save_without_trace_succeeds(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {
        "data": _pipeline(
            make_video(vid="VID-001", status="待拍", topic="紅茶測試", title="封面標題")
        ),
        "op_paths": {},
    }
    monkeypatch.setattr(
        video_ops.sys, "argv", _argv("--skill", "generation", "--mode", "dual-track")
    )

    video_ops._cmd_save(ctx)

    out = capsys.readouterr().out
    assert "VID：VID-001" in out
    assert "主題：紅茶測試" in out
    assert "skill：generation" in out
    assert "mode：dual-track" in out
    assert "hook_type：B2" in out
    assert "title 候選：封面標題" in out
    assert "verifier_prediction=high" in out


def test_save_quiet_suppresses_success_stdout(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": _pipeline(make_video(vid="VID-001", status="待拍", topic="紅茶測試")), "op_paths": {}}
    monkeypatch.setattr(video_ops.sys, "argv", _argv("--quiet"))

    video_ops._cmd_save(ctx)

    assert capsys.readouterr().out == ""
