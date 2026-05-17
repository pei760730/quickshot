import pytest

from tests.path_bootstrap import load_rules_lint_module

rules_lint = load_rules_lint_module("rules_lint_pipeline_guard")


def _base_pipeline():
    return {
        "_meta": {"next_vid": 78, "next_idea_id": 210},
        "items": [
            {"vid": "VID-009", "status": "已上線", "backfill": "BF-1"},
            {"vid": "VID-010", "status": "待拍", "backfill": None},
        ],
    }


def test_next_vid_regression_error():
    base = _base_pipeline()
    head = _base_pipeline()
    head["_meta"]["next_vid"] = 61

    issues = rules_lint.evaluate_pipeline_regression_guard(base, head)

    assert any("next_vid" in i for i in issues)


def test_status_online_to_pending_error():
    base = _base_pipeline()
    head = _base_pipeline()
    head["items"][0]["status"] = "待拍"

    issues = rules_lint.evaluate_pipeline_regression_guard(base, head)

    assert any("VID-009 status 已上線 → 待拍" in i for i in issues)


def test_backfill_erased_error():
    base = _base_pipeline()
    head = _base_pipeline()
    head["items"][0]["backfill"] = None

    issues = rules_lint.evaluate_pipeline_regression_guard(base, head)

    assert any("VID-009 backfill" in i for i in issues)


def test_override_string_skips(monkeypatch):
    errors = []
    monkeypatch.setenv("PR_BODY", "pipeline-override justified by: incident rollback")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")

    rules_lint.check_pipeline_regression_guard(errors)

    assert errors == []


def test_main_push_skips(monkeypatch):
    errors = []
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")

    rules_lint.check_pipeline_regression_guard(errors)

    assert errors == []


def test_pure_new_vid_passes():
    base = _base_pipeline()
    head = _base_pipeline()
    head["items"].append({"vid": "VID-011", "status": "待拍", "backfill": None})

    issues = rules_lint.evaluate_pipeline_regression_guard(base, head)

    assert issues == []
