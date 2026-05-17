"""Regression tests for rules-lint missing-file path resolution."""

from pathlib import Path

from path_bootstrap import load_rules_lint_module


def test_missing_file_checker_accepts_docs_references(tmp_path):
    rules_lint = load_rules_lint_module()
    repo_root = tmp_path
    wf = repo_root / ".claude" / "rules" / "workflow.md"
    wf.parent.mkdir(parents=True)
    wf.write_text("見 production-details.md\n", encoding="utf-8")

    docs_ref = repo_root / "docs" / "references" / "production-details.md"
    docs_ref.parent.mkdir(parents=True)
    docs_ref.write_text("# ok\n", encoding="utf-8")

    rules_lint.REPO_ROOT = repo_root
    errors = []
    rules_lint.check_file_references(
        wf.read_text(encoding="utf-8"),
        wf,
        {"deprecated_files": {}, "rules_files": {}},
        errors,
    )

    missing = [e for e in errors if e.get("check") == "missing_file"]
    assert missing == []


def test_missing_file_checker_accepts_bare_filename_elsewhere_in_repo(tmp_path):
    rules_lint = load_rules_lint_module()
    repo_root = tmp_path
    wf = repo_root / ".claude" / "rules" / "workflow.md"
    wf.parent.mkdir(parents=True)
    wf.write_text("Codex 不讀 `brand.md`\n", encoding="utf-8")

    brand = repo_root / "01-data-brain" / "brand.md"
    brand.parent.mkdir(parents=True)
    brand.write_text("# brand\n", encoding="utf-8")

    rules_lint.REPO_ROOT = repo_root
    errors = []
    rules_lint.check_file_references(
        wf.read_text(encoding="utf-8"),
        wf,
        {"deprecated_files": {}, "rules_files": {}},
        errors,
    )

    missing = [e for e in errors if e.get("check") == "missing_file"]
    assert missing == []


def test_ready_to_shoot_ai_patterns_are_excluded_from_rules_lint():
    rules_lint = load_rules_lint_module()
    errors = []

    rules_lint.check_ai_patterns_warnings(errors)

    assert errors == []
