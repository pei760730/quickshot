from path_bootstrap import load_video_ops_module


def _argv(*extra):
    return [
        "video-ops.py", "record-verifier-scores", "VID-001",
        "--conflict-score", "8",
        "--retention-prediction", "A",
        "--ai-residue-count", "0",
        "--data-consistency", "true",
        "--format-complete", "true",
        "--pass-count", "5/5",
        *extra,
    ]


def test_record_verifier_scores_prints_health_summary(monkeypatch, capsys):
    video_ops = load_video_ops_module()
    monkeypatch.setattr(video_ops, "load_tracking", lambda: {"videos": [{"vid": "VID-001"}]})
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (True, "VID-001 verifier_scores 已記錄（5/5）"))
    monkeypatch.setattr(video_ops.sys, "argv", _argv())

    video_ops.main()

    out = capsys.readouterr().out
    assert "體檢摘要" in out
    assert "衝突分數：8/10" in out
    assert "留存預測：A" in out
    assert "AI 殘留數：0" in out
    assert "資料一致性：通過" in out
    assert "5 項通過數：5/5" in out
    assert "建議：可進入拍攝" in out


def test_record_verifier_scores_quiet_suppresses_success_stdout(monkeypatch, capsys):
    video_ops = load_video_ops_module()
    monkeypatch.setattr(video_ops, "load_tracking", lambda: {"videos": [{"vid": "VID-001"}]})
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(video_ops.sys, "argv", _argv("--quiet"))

    video_ops.main()

    assert capsys.readouterr().out == ""
