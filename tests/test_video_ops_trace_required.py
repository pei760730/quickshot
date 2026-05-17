import importlib.util
import io
import json
from contextlib import redirect_stdout

import pytest

from lib.pipeline import add_video


spec = importlib.util.spec_from_file_location("video_ops", "scripts/ops/video-ops.py")
video_ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video_ops)


def _base_save_argv(vid):
    return [
        "video-ops.py",
        "save",
        vid,
        "--script-path",
        "03-production-line/02-ready-to-shoot/test.md",
        "--title-type",
        "T1",
        "--hook-type",
        "B2",
        "--version",
        "B2",
        "--verifier-prediction",
        "high",
    ]


def test_trace_required_status_missing_trace_exit_1(patch_paths, monkeypatch):
    data = video_ops.load_tracking()
    data["_meta"]["trace_required_statuses"] = ["已上線"]
    add_video(data, "t", "tag", title="tt", source="quick-shot", initial_status="已上線")
    data["videos"][0]["source"] = "pipeline"

    monkeypatch.setattr(video_ops.sys, "argv", _base_save_argv("VID-001"))
    with pytest.raises(SystemExit) as ei:
        video_ops._cmd_save({"data": data, "op_paths": {}})
    assert ei.value.code == 1


def test_extract_fenced_json_and_parse_ok():
    block = """```json
{\"generation_trace\": {\"skill_used\": \"generation\", \"mode\": \"dual-track\"}}
```"""
    extracted = video_ops._extract_fenced_json_from_stdin(block)
    payload = json.loads(extracted)
    assert payload["generation_trace"]["skill_used"] == "generation"


def test_save_with_trace_from_stdin_bad_json_exit_1(patch_paths, monkeypatch):
    data = video_ops.load_tracking()
    add_video(data, "t", "tag", title="tt", source="quick-shot", initial_status="已上線")
    data["videos"][0]["source"] = "pipeline"
    data["_meta"]["trace_required_statuses"] = ["已上線"]
    monkeypatch.setattr(video_ops.sys, "stdin", io.StringIO("```json\n{bad}\n```"))
    monkeypatch.setattr(video_ops.sys, "argv", _base_save_argv("VID-001").copy())
    video_ops.sys.argv[1] = "save-with-trace-from-stdin"
    with pytest.raises(SystemExit) as ei:
        video_ops._cmd_save_with_trace_from_stdin({"data": data, "op_paths": {}})
    assert ei.value.code == 1


def test_adoption_stats_numbers(patch_paths, monkeypatch):
    data = video_ops.load_tracking()
    vids = []
    for i in range(1, 6):
        add_video(data, f"t{i}", "tag", title=f"tt{i}", source="quick-shot", initial_status="已上線")
        v = data["videos"][-1]
        v["source"] = "pipeline"
        v["publish_date"] = f"2026-04-0{i}"
        vids.append(v)
    vids[0]["hook_type"] = "B1"
    vids[1]["hook_type"] = "B2"
    vids[0]["generation_trace"] = {"skill_used": "generation", "mode": "dual-track"}
    vids[1]["generation_trace"] = {"skill_used": "quality", "mode": "single"}
    vids[2]["generation_trace"] = {"skill_used": "generation", "mode": "single"}
    vids[0]["verifier_scores"] = {"conflict_score": 8}

    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "adoption-stats", "--n", "5"])
    monkeypatch.setattr(video_ops, "datetime", type("T", (), {
        "utcnow": staticmethod(lambda: __import__("datetime").datetime(2026, 4, 10)),
        "strptime": staticmethod(__import__("datetime").datetime.strptime),
    }))
    out = io.StringIO()
    with redirect_stdout(out):
        video_ops._cmd_adoption_stats({"data": data, "op_paths": {}})
    s = out.getvalue()
    assert "hook_type: 2/5 (40.0%)" in s
    assert "generation_trace: 3/5 (60.0%)" in s
    assert "verifier_scores: 1/5 (20.0%)" in s
