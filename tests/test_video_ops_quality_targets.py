"""High-ROI quality tests for video-ops: e2e flow + fault injection."""

import subprocess
import sys

from lib.pipeline import add_video, load_tracking, save_tracking, transition
from lib.validate import validate_all
from path_bootstrap import video_ops_script_path
from timeouts import PROCESS_TIMEOUT_SEC


def test_e2e_add_transition_validate_all(patch_paths):
    """End-to-end business flow: add -> transition -> validate-all should remain clean."""
    data = load_tracking()
    script_rel = "03-production-line/02-ready-to-shoot/2026-03-17_e2e_腳本_V1.md"

    vid = add_video(
        data,
        "E2E 主題",
        "E2E標籤",
        title="E2E標題",
        source="quick-shot",
        script_path=script_rel,
    )

    script_file = patch_paths / script_rel
    script_file.parent.mkdir(parents=True, exist_ok=True)
    script_file.write_text(f"> 影片碼：{vid}\n---\nE2E 腳本", encoding="utf-8")

    ok, msg = transition(data, vid, "剪輯中")
    assert ok, msg
    ok, msg = transition(data, vid, "已上線")
    assert ok, msg

    save_tracking(data)
    result = validate_all(data)
    assert result["errors"] == []


def test_fault_injection_missing_required_field_is_reported(patch_paths):
    """Fault injection: damaged record should be surfaced by validate-all."""
    data = load_tracking()
    add_video(
        data,
        "Fault 主題",
        "Fault標籤",
        title="Fault標題",
        source="quick-shot",
    )
    data["videos"][0]["title"] = ""

    result = validate_all(data)
    assert any("缺少 title" in err for err in result["errors"])


def test_fault_injection_invalid_operator_cli():
    """Fault injection: invalid --operator must fail fast and clearly."""
    script = video_ops_script_path()
    result = subprocess.run(
        [sys.executable, str(script), "--operator", "not-an-operator", "list"],
        capture_output=True,
        text=True,
        check=False,
        timeout=PROCESS_TIMEOUT_SEC,
    )
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0
    assert "未知操作員" in combined


def test_fault_injection_malformed_video_data_fails_gracefully():
    """Fault injection: validate-all should report shape error instead of crashing."""
    result = validate_all({"_meta": {"version": "broken"}})
    assert result["warnings"] == []
    assert result["migrate_candidates"] == []
    assert result["errors"] == ["pipeline.json 結構錯誤：缺少 videos 陣列"]


def test_fault_injection_wrong_videos_type_reports_actual_type():
    """Feature: shape guard should include actual type for faster diagnosis."""
    result = validate_all({"videos": {}})
    assert result["warnings"] == []
    assert result["migrate_candidates"] == []
    assert result["errors"] == ["pipeline.json 結構錯誤：videos 應為陣列，實際為 dict"]
