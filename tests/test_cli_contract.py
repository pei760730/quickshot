import re
from pathlib import Path

import pytest
from path_bootstrap import load_video_ops_module


def _load(path):
    return Path(path).read_text(encoding="utf-8")


def _extract_doc_rows(text):
    rows = {}
    for line in text.splitlines():
        m = re.match(r"\| `([^`]+)` \| `([^`]+)` \|", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def test_contract_transition_to_flag_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "--to" in doc.get("transition", "")
    assert "kv.get(\"to\")" in impl


def test_contract_quick_add_status_flag_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "--initial-status" in doc.get("quick-add", "")
    assert "initial_status\") or kv.get(\"status\"" in impl




def test_contract_quick_add_hook_type_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "--hook-type" in doc.get("quick-add", "")
    assert 'hook_type = kv.get("hook_type")' in impl


def test_contract_batch_quick_add_hook_type_matches_impl():
    contract_doc = _load("docs/contracts/video-ops-cli.md")
    impl = _load("scripts/ops/video-ops.py")
    assert "batch-quick-add" in contract_doc and "hook_type" in contract_doc
    assert 'hook_type = it.get("hook_type")' in impl


def test_contract_set_hook_type_command_exists():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "set-hook-type" in doc
    assert '"set-hook-type": _cmd_set_hook_type' in impl


def test_contract_set_hook_type_hook_type_flag_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "--hook-type" in doc.get("set-hook-type", "")
    assert 'hook_type = kv.get("hook_type")' in impl


def test_contract_set_hook_type_vid_position_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "set-hook-type VID-NNN" in doc.get("set-hook-type", "")
    assert "vid = sys.argv[2]" in impl


def test_contract_add_tag_optional_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    assert "--tag" in doc.get("add", "")
    assert "⚠️ 未提供 --tag" in impl


def test_contract_record_verifier_scores_required_flags_match_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    usage = doc.get("record-verifier-scores", "")
    assert "--conflict-score" in usage
    assert "--retention-prediction" in usage
    assert "--ai-residue-count" in usage
    assert "--data-consistency" in usage
    assert "--format-complete" in usage
    assert "--pass-count" in usage
    assert "_parse_bool_arg" in impl
    assert "required_flags = {" in impl


def test_contract_save_verifier_scores_flag_matches_impl():
    doc = _extract_doc_rows(_load("docs/contracts/video-ops-cli.md"))
    impl = _load("scripts/ops/video-ops.py")
    usage = doc.get("save", "")
    assert "--verifier-scores" in usage
    assert "raw_verifier_scores = kv.get(\"verifier_scores\")" in impl



def test_transition_to_alias_runtime(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": []}, "op_paths": {"operator": "kai", "vid_prefix": "VID"}}
    monkeypatch.setattr(video_ops, "transition", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "transition", "VID-001", "--to", "剪輯中"])
    video_ops._cmd_transition(ctx)
    out = capsys.readouterr().out
    assert "✅" in out


def test_quick_add_initial_status_alias_runtime(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": []}, "op_paths": {"vid_prefix": "VID"}}
    monkeypatch.setattr(video_ops, "add_video", lambda *_args, **_kwargs: "VID-001")
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        ["video-ops.py", "quick-add", "--topic", "t", "--tag", "g", "--title", "tt", "--initial-status", "已上線"],
    )
    video_ops._cmd_quick_add(ctx)
    out = capsys.readouterr().out
    assert "已上線" in out


def test_add_without_tag_warn_and_exit_zero(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": []}, "op_paths": {"vid_prefix": "VID"}}
    monkeypatch.setattr(video_ops, "add_video", lambda *_args, **_kwargs: "VID-002")
    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "add", "--topic", "x", "--title", "y"])
    video_ops._cmd_add(ctx)
    out = capsys.readouterr().out
    assert "⚠️ 未提供 --tag" in out
    assert "✅ 已新增 VID-002" in out


def test_set_hook_type_runtime(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": []}, "op_paths": {"tracking_json": "data/kai/tracking.json"}}
    monkeypatch.setattr(video_ops, "set_hook_type", lambda *_args, **_kwargs: (True, "VID-001 hook_type = B2（原未設）"))
    monkeypatch.setattr(video_ops.sys, "argv", ["video-ops.py", "set-hook-type", "VID-001", "--hook-type", "B2"])
    video_ops._cmd_set_hook_type(ctx)
    out = capsys.readouterr().out
    assert "✅ VID-001 hook_type = B2（原未設）" in out


def test_record_verifier_scores_invalid_bool_exits(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    monkeypatch.setattr(video_ops, "load_tracking", lambda: {"videos": []})
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "record-verifier-scores",
            "VID-001",
            "--data-consistency",
            "yes",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "data_consistency 必須為 true 或 false" in out


def test_record_verifier_scores_unknown_flag_exits(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    monkeypatch.setattr(video_ops, "load_tracking", lambda: {"videos": []})
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "record-verifier-scores",
            "VID-001",
            "--unknown-flag",
            "x",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "不支援的參數" in out
    assert "--unknown-flag" in out


def test_record_verifier_scores_dangling_flag_exits(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    monkeypatch.setattr(video_ops, "load_tracking", lambda: {"videos": []})
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "record-verifier-scores",
            "VID-001",
            "--conflict-score",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "無法解析的參數" in out
    assert "--conflict-score" in out


def test_record_verifier_scores_missing_required_flags_exits(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    monkeypatch.setattr(video_ops, "load_tracking", lambda: {"videos": []})
    called = {"recorded": False}

    def _fake_record(*_args, **_kwargs):
        called["recorded"] = True
        return True, "ok"

    monkeypatch.setattr(video_ops, "record_verifier_scores", _fake_record)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "record-verifier-scores",
            "VID-001",
            "--conflict-score",
            "8",
            "--retention-prediction",
            "A",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "缺少必填參數" in out
    assert "--ai-residue-count" in out
    assert "--data-consistency" in out
    assert "--format-complete" in out
    assert "--pass-count" in out
    assert called["recorded"] is False


def test_save_success_prints_verifier_scores_reminder(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": [{"vid": "VID-001"}]}, "op_paths": {"operator": "kai"}}
    monkeypatch.setattr(video_ops, "save_script", lambda *_args, **_kwargs: (True, "VID-001 已存檔"))
    monkeypatch.setattr(video_ops, "find_video", lambda *_args, **_kwargs: (0, {"vid": "VID-001"}))
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
        ],
    )

    video_ops._cmd_save(ctx)
    out = capsys.readouterr().out
    assert "✅ VID-001 已存檔" in out
    assert "尚未記錄 verifier_scores" in out


def test_save_no_reminder_when_verifier_scores_exists(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": [{"vid": "VID-001"}]}, "op_paths": {"operator": "kai"}}
    monkeypatch.setattr(video_ops, "save_script", lambda *_args, **_kwargs: (True, "VID-001 已存檔"))
    monkeypatch.setattr(
        video_ops,
        "find_video",
        lambda *_args, **_kwargs: (0, {"vid": "VID-001", "verifier_scores": {"pass_count": "5/5"}}),
    )
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
        ],
    )

    video_ops._cmd_save(ctx)
    out = capsys.readouterr().out
    assert "✅ VID-001 已存檔" in out
    assert "尚未記錄 verifier_scores" not in out


def test_save_with_verifier_scores_json_records_in_same_run(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": [{"vid": "VID-001"}]}, "op_paths": {"operator": "kai"}}
    monkeypatch.setattr(video_ops, "save_script", lambda *_args, **_kwargs: (True, "VID-001 已存檔"))
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (True, "VID-001 verifier_scores 已記錄（5/5）"))
    monkeypatch.setattr(video_ops, "find_video", lambda *_args, **_kwargs: (0, {"vid": "VID-001"}))
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
            "--verifier-scores",
            '{"conflict_score":8,"retention_prediction":"A","ai_residue_count":0,"data_consistency":true,"format_complete":true,"pass_count":"5/5"}',
        ],
    )

    video_ops._cmd_save(ctx)
    out = capsys.readouterr().out
    assert "✅ VID-001 已存檔" in out
    assert "✅ VID-001 verifier_scores 已記錄（5/5）" in out
    assert "尚未記錄 verifier_scores" not in out


def test_save_with_invalid_verifier_scores_fails_before_save(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": [{"vid": "VID-001"}]}, "op_paths": {"operator": "kai"}}
    called = {"save_script": False}

    def _fake_save(*_args, **_kwargs):
        called["save_script"] = True
        return True, "VID-001 已存檔"

    monkeypatch.setattr(video_ops, "save_script", _fake_save)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
            "--verifier-scores",
            '{"conflict_score":11}',
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_save(ctx)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "--verifier-scores 驗證失敗" in out
    assert called["save_script"] is False


def test_save_with_unknown_verifier_scores_field_fails_before_save(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {"data": {"videos": [{"vid": "VID-001"}]}, "op_paths": {"operator": "kai"}}
    called = {"save_script": False}

    def _fake_save(*_args, **_kwargs):
        called["save_script"] = True
        return True, "VID-001 已存檔"

    monkeypatch.setattr(video_ops, "save_script", _fake_save)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
            "--verifier-scores",
            '{"conflict_socre":8,"retention_prediction":"A","ai_residue_count":0,"data_consistency":true,"format_complete":true,"pass_count":"5/5"}',
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_save(ctx)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "--verifier-scores 驗證失敗" in out
    assert "不支援的欄位" in out
    assert called["save_script"] is False


def test_save_with_verifier_scores_failure_rolls_back(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {
        "data": {"videos": [{"vid": "VID-001", "state": "before"}]},
        "op_paths": {"operator": "kai", "tracking_json": "data/kai/tracking.json"},
    }
    save_tracking_called = {"called": False}

    def _fake_save_script(data, *_args, **_kwargs):
        data["videos"][0]["state"] = "after-save"
        return True, "VID-001 已存檔"

    def _fake_save_tracking(data, *_args, **kwargs):
        save_tracking_called["called"] = True
        assert data["videos"][0]["state"] == "before"
        assert kwargs.get("tracking_json") == "data/kai/tracking.json"

    monkeypatch.setattr(video_ops, "save_script", _fake_save_script)
    monkeypatch.setattr(video_ops, "record_verifier_scores", lambda *_args, **_kwargs: (False, "驗證失敗"))
    monkeypatch.setattr(video_ops, "save_tracking", _fake_save_tracking)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
            "--verifier-scores",
            '{"conflict_score":8,"retention_prediction":"A","ai_residue_count":0,"data_consistency":true,"format_complete":true,"pass_count":"5/5"}',
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_save(ctx)
    assert exc.value.code == 1
    assert ctx["data"]["videos"][0]["state"] == "before"
    assert save_tracking_called["called"] is True
    out = capsys.readouterr().out
    assert "已回滾 save 變更" in out


def test_save_with_verifier_scores_exception_rolls_back(monkeypatch, patch_paths, capsys):
    video_ops = load_video_ops_module()
    ctx = {
        "data": {"videos": [{"vid": "VID-001", "state": "before"}]},
        "op_paths": {"operator": "kai", "tracking_json": "data/kai/tracking.json"},
    }
    save_tracking_called = {"called": False}

    def _fake_save_script(data, *_args, **_kwargs):
        data["videos"][0]["state"] = "after-save"
        return True, "VID-001 已存檔"

    def _fake_save_tracking(data, *_args, **kwargs):
        save_tracking_called["called"] = True
        assert data["videos"][0]["state"] == "before"
        assert kwargs.get("tracking_json") == "data/kai/tracking.json"

    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(video_ops, "save_script", _fake_save_script)
    monkeypatch.setattr(video_ops, "record_verifier_scores", _boom)
    monkeypatch.setattr(video_ops, "save_tracking", _fake_save_tracking)
    monkeypatch.setattr(
        video_ops.sys,
        "argv",
        [
            "video-ops.py",
            "save",
            "VID-001",
            "--script-path",
            "x.md",
            "--title-type",
            "T1",
            "--hook-type",
            "B1",
            "--version",
            "V1",
            "--verifier-prediction",
            "high",
            "--trace",
            '{"skill_used":"generation","skill_version":"4.7","generated_at":"2026-05-07","title_type":"T1","hook_type":"B1","version_chosen":"B"}',
            "--verifier-scores",
            '{"conflict_score":8,"retention_prediction":"A","ai_residue_count":0,"data_consistency":true,"format_complete":true,"pass_count":"5/5"}',
        ],
    )

    with pytest.raises(SystemExit) as exc:
        video_ops._cmd_save(ctx)
    assert exc.value.code == 1
    assert ctx["data"]["videos"][0]["state"] == "before"
    assert save_tracking_called["called"] is True
    out = capsys.readouterr().out
    assert "已回滾 save 變更（因 verifier_scores 寫入例外）" in out
    assert "寫入發生例外" in out
