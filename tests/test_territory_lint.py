from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "lint" / "territory-lint.py"

spec = importlib.util.spec_from_file_location("territory_lint", SCRIPT_PATH)
territory_lint = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(territory_lint)


def run_lint(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_codex_branch_allows_scripts_path() -> None:
    result = run_lint("--branch", "codex/x", "--files", "scripts/foo.py")

    assert result.returncode == 0
    assert "passed" in result.stdout


def test_codex_branch_denies_claude_md() -> None:
    result = run_lint("--branch", "codex/x", "--files", "CLAUDE.md")

    assert result.returncode == 1
    assert "CLAUDE.md" in result.stdout
    assert "deny" in result.stdout


def test_non_codex_branch_skips_lint() -> None:
    result = run_lint("--branch", "feature/x", "--files", "CLAUDE.md")

    assert result.returncode == 0
    assert "skipped" in result.stdout


def test_path_matches_double_star_across_layers() -> None:
    assert territory_lint.path_matches("scripts/lint/territory-lint.py", "scripts/**")
    assert territory_lint.path_matches("docs/contracts/path/file.md", "docs/**/file.md")


def test_path_matches_single_star_single_layer_only() -> None:
    assert territory_lint.path_matches("tests/foo.py", "tests/*.py")
    assert not territory_lint.path_matches("tests/unit/foo.py", "tests/*.py")


def test_path_matches_normalizes_windows_backslashes() -> None:
    assert territory_lint.path_matches(r"scripts\lint\territory-lint.py", "scripts/**")
    assert territory_lint.path_matches(r".github\agent-territory.json", ".github/agent-territory.json")
