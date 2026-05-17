"""Guard rails for video-ops command dispatch structure."""

import ast
import os
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from typing import Sequence

import pytest

from lib.config import DEFAULT_OPERATOR, get_operator_paths
from lib.pipeline import get_pipeline_data
from path_bootstrap import video_ops_script_path
from timeouts import PROCESS_TIMEOUT_SEC

VIDEO_OPS_PATH = video_ops_script_path()
UNKNOWN_CMD_FALLBACK = "未知指令"


def _default_operator_has_pipeline_items() -> bool:
    try:
        paths = get_operator_paths(DEFAULT_OPERATOR)
        pipeline_path = Path(paths["data_dir"]) / "pipeline.json"
        payload = get_pipeline_data(pipeline_json=pipeline_path)
        if payload is None:
            return False
        return len(payload.get("items", [])) > 0
    except Exception:
        return False


def _run_video_ops(cmd: Sequence[str]) -> tuple[CompletedProcess[str], str]:
    """Execute video-ops CLI with cmd args and return (CompletedProcess, combined_output)."""
    env = {**os.environ, "PYTHONPATH": str(VIDEO_OPS_PATH.parent)}
    result = subprocess.run(
        [sys.executable, str(VIDEO_OPS_PATH), *cmd],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=PROCESS_TIMEOUT_SEC,
    )
    return result, f"{result.stdout}\n{result.stderr}"


def test_simple_handlers_are_not_duplicated_in_main_branch_chain():
    """Commands in SIMPLE_COMMAND_HANDLERS should not have explicit cmd branches in main()."""
    source = VIDEO_OPS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    handler_keys = set()
    branched_cmds = set()

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SIMPLE_COMMAND_HANDLERS":
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                handler_keys.add(key.value)

        if isinstance(node, ast.FunctionDef) and node.name == "main":
            for stmt in ast.walk(node):
                if not isinstance(stmt, ast.If):
                    continue
                test = stmt.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "cmd"
                    and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Eq)
                    and len(test.comparators) == 1
                    and isinstance(test.comparators[0], ast.Constant)
                    and isinstance(test.comparators[0].value, str)
                ):
                    branched_cmds.add(test.comparators[0].value)

    duplicated = handler_keys & branched_cmds
    assert not duplicated, f"Duplicated cmd branch(es) found in main(): {sorted(duplicated)}"


def test_simple_handler_table_has_unique_keys_and_defined_handlers():
    """SIMPLE_COMMAND_HANDLERS should avoid silent key overwrite and only map defined _cmd_* funcs."""
    source = VIDEO_OPS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    handler_keys = []
    handler_func_names = []
    defined_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SIMPLE_COMMAND_HANDLERS":
                if isinstance(node.value, ast.Dict):
                    for key, value in zip(node.value.keys, node.value.values):
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            handler_keys.append(key.value)
                        if isinstance(value, ast.Name):
                            handler_func_names.append(value.id)

    assert len(handler_keys) == len(set(handler_keys)), (
        f"Duplicate command key(s) in SIMPLE_COMMAND_HANDLERS: {handler_keys}"
    )
    missing = sorted(name for name in handler_func_names if name not in defined_functions)
    assert not missing, f"Undefined handler function(s) in SIMPLE_COMMAND_HANDLERS: {missing}"
    non_cmd_handlers = sorted(name for name in handler_func_names if not name.startswith("_cmd_"))
    assert not non_cmd_handlers, (
        "Handler mapping should point to _cmd_* functions only: "
        f"{non_cmd_handlers}"
    )

    cmd_func_arg_mismatch = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name in handler_func_names:
            if len(node.args.args) != 1:
                cmd_func_arg_mismatch.append(node.name)
    assert not cmd_func_arg_mismatch, (
        "Mapped handler function(s) should accept exactly one ctx arg: "
        f"{sorted(cmd_func_arg_mismatch)}"
    )


@pytest.mark.skipif(
    not _default_operator_has_pipeline_items(),
    reason="smoke test requires non-empty pipeline in default operator (kai-seeded main repo)",
)
@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        (["list"], "VID-"),
        (["next-vid"], "VID-"),
        (["list-ideas"], "IDEA-"),
        (["query-pending-scripts"], "腳本待補"),
        (["analyze-deviations"], "偏差"),
    ],
)
def test_selected_simple_handler_commands_do_not_traceback(cmd, expected):
    """Smoke test read-only simple handlers to ensure dispatch is runtime-stable."""
    result, combined = _run_video_ops(cmd)
    assert result.returncode == 0, (
        f"unexpected non-zero exit for command: {' '.join(cmd)}\n{combined}"
    )
    assert combined.strip(), f"empty output for command: {' '.join(cmd)}"
    if expected:
        assert expected in combined, (
            f"expected marker not found for command: {' '.join(cmd)} ({expected})\n{combined}"
        )
    assert "Traceback (most recent call last)" not in combined, (
        f"unexpected traceback for command: {' '.join(cmd)}\n{combined}"
    )
    assert UNKNOWN_CMD_FALLBACK not in combined, (
        f"command resolved to unknown-command path unexpectedly: {' '.join(cmd)}\n{combined}"
    )


@pytest.mark.parametrize(
    ("cmd", "expected"),
    [
        (["list-topics"], "━━ 🎬 影片 ━━"),
        (["validate"], "驗證"),
        (["validate-all"], "跨檔驗證報告"),
    ],
)
def test_selected_legacy_commands_still_run_after_simple_dispatch_refactor(cmd, expected):
    """Smoke test selected legacy branches still run after simple-handler dispatch phase."""
    result, combined = _run_video_ops(cmd)
    assert result.returncode == 0, (
        f"unexpected non-zero exit for legacy command: {' '.join(cmd)}\n{combined}"
    )
    assert combined.strip(), f"empty output for legacy command: {' '.join(cmd)}"
    assert expected in combined, (
        f"expected marker not found for legacy command: {' '.join(cmd)} ({expected})\n{combined}"
    )
    assert "Traceback (most recent call last)" not in combined, (
        f"unexpected traceback for legacy command: {' '.join(cmd)}\n{combined}"
    )
    assert UNKNOWN_CMD_FALLBACK not in combined, (
        f"legacy command resolved to unknown-command path unexpectedly: {' '.join(cmd)}\n{combined}"
    )
