import importlib.util
import io
import json
from contextlib import redirect_stdout


spec = importlib.util.spec_from_file_location("video_ops", "scripts/ops/video-ops.py")
video_ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video_ops)


def test_adoption_stats_vid_inference_flag(tmp_path, monkeypatch):
    log_dir = tmp_path / "data/.adoption-stats"
    log_dir.mkdir(parents=True)
    log = log_dir / "vid_inference.jsonl"
    rows = []
    # 30d: 11 fenced, 9 inferred => 18.2% miss (alert)
    for i in range(11):
        rows.append({"ts": f"2026-04-{10 + i:02d}T10:00:00+00:00", "had_fenced": True, "vid_inferred": i < 9})
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    monkeypatch.setattr(video_ops, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "adoption-stats", "--vid-inference", "true"])
    monkeypatch.setattr(video_ops, "datetime", type("T", (), {
        "utcnow": staticmethod(lambda: __import__("datetime").datetime(2026, 4, 29)),
        "strptime": staticmethod(__import__("datetime").datetime.strptime),
        "fromisoformat": staticmethod(__import__("datetime").datetime.fromisoformat),
    }))

    out = io.StringIO()
    with redirect_stdout(out):
        video_ops._cmd_adoption_stats({"data": {"videos": []}, "op_paths": {}})
    s = out.getvalue()
    assert "last 7d:" in s
    assert "last 30d:  fenced_blocks=11, vid_inferred=9, miss_rate=18.2%" in s
    assert "alert: ⚠️ miss_rate > 10% (last 30d)" in s
