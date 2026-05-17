"""Shared sys.path bootstrap utilities for pytest runtime.

Contract doc: docs/contracts/test-path-bootstrap.md
"""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import MutableSequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OPS_LIB_ROOT = PROJECT_ROOT / "scripts" / "ops"
ENGINE_LIB_ROOT = PROJECT_ROOT / "scripts" / "engine"
UTILS_LIB_ROOT = PROJECT_ROOT / "scripts" / "utils"
VIDEO_OPS_SCRIPT = PROJECT_ROOT / "scripts" / "ops" / "video-ops.py"
RULES_LINT_SCRIPT = PROJECT_ROOT / "scripts" / "lint" / "rules-lint.py"


def _canonical_path(value: str) -> str:
    if value == "":
        return value
    return str(Path(value).resolve())


def prepend_sys_path(path: Path, path_list: MutableSequence[str] | None = None) -> bool:
    """Ensure path exists once at the front and report whether list changed."""
    target = _canonical_path(str(path))
    target_list = sys.path if path_list is None else path_list

    original = list(target_list)
    target_list[:] = [p for p in target_list if _canonical_path(p) != target]
    target_list.insert(0, target)
    return list(target_list) != original


def bootstrap_test_sys_path(path_list: MutableSequence[str] | None = None) -> tuple[str, str]:
    """Ensure both modern and legacy import paths are available for tests."""
    prepend_sys_path(PROJECT_ROOT, path_list)
    prepend_sys_path(OPS_LIB_ROOT, path_list)
    return str(PROJECT_ROOT), str(OPS_LIB_ROOT)


def bootstrap_engine_test_sys_path(path_list: MutableSequence[str] | None = None) -> str:
    """Ensure engine scripts are importable as top-level modules in tests."""
    prepend_sys_path(ENGINE_LIB_ROOT, path_list)
    return str(ENGINE_LIB_ROOT)


def bootstrap_utils_test_sys_path(path_list: MutableSequence[str] | None = None) -> str:
    """Ensure utils scripts are importable as top-level modules in tests."""
    prepend_sys_path(UTILS_LIB_ROOT, path_list)
    return str(UTILS_LIB_ROOT)


def video_ops_script_path() -> Path:
    """Canonical path to scripts/ops/video-ops.py for CLI tests."""
    return VIDEO_OPS_SCRIPT


def load_video_ops_module(module_name: str = "video_ops"):
    """Load scripts/ops/video-ops.py as a module for CLI contract tests."""
    return _load_module_from_path(video_ops_script_path(), module_name)


def load_rules_lint_module(module_name: str = "rules_lint"):
    """Load scripts/lint/rules-lint.py as a module for lint tests."""
    return _load_module_from_path(RULES_LINT_SCRIPT, module_name)


def load_module_from_repo(relative_path: str, module_name: str):
    """Load an arbitrary repo-relative Python script as a module."""
    return _load_module_from_path(PROJECT_ROOT / relative_path, module_name)


def _load_module_from_path(script_path: Path, module_name: str):
    if not script_path.is_file():
        raise ImportError(f"Unable to load module '{module_name}' from '{script_path}'")
    spec = spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module '{module_name}' from '{script_path}'")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
