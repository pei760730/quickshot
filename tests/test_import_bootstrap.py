import importlib
import sys
from pathlib import Path

import pytest

from path_bootstrap import (
    ENGINE_LIB_ROOT,
    OPS_LIB_ROOT,
    PROJECT_ROOT,
    bootstrap_engine_test_sys_path,
    bootstrap_test_sys_path,
    bootstrap_utils_test_sys_path,
    load_module_from_repo,
    load_rules_lint_module,
    load_video_ops_module,
    prepend_sys_path,
    video_ops_script_path,
)

ROOT_S = str(PROJECT_ROOT)
OPS_S = str(OPS_LIB_ROOT)
ENGINE_S = str(ENGINE_LIB_ROOT)
UTILS_S = str(PROJECT_ROOT / "scripts" / "utils")
VIDEO_OPS_S = str(PROJECT_ROOT / "scripts" / "ops" / "video-ops.py")


def test_scripts_package_importable():
    module = importlib.import_module("scripts.libs.brain_loader")
    assert hasattr(module, "load_for_skill")


def test_legacy_lib_importable():
    module = importlib.import_module("lib.config")
    assert hasattr(module, "PROJECT_ROOT")


def test_bootstrap_paths_fixture_contract(bootstrap_paths):
    repo_root_s, ops_path_s = bootstrap_paths
    assert (repo_root_s, ops_path_s) == (ROOT_S, OPS_S)
    assert repo_root_s in sys.path
    assert ops_path_s in sys.path
    assert sys.path.index(ops_path_s) < sys.path.index(repo_root_s)


@pytest.mark.parametrize(
    "seed_path",
    [
        ["seed"],
        [ROOT_S, "seed", OPS_S, ROOT_S, OPS_S],
        [OPS_S, ROOT_S, "seed"],
        ["seed-a", ROOT_S, "seed-b", OPS_S, "seed-c", ROOT_S],
        ["", ".", ROOT_S, "", OPS_S],
    ],
)
def test_bootstrap_paths_are_ordered(seed_path):
    local_path = list(seed_path)
    boot_repo_root_s, boot_ops_path_s = bootstrap_test_sys_path(local_path)

    assert (boot_repo_root_s, boot_ops_path_s) == (ROOT_S, OPS_S)
    assert local_path[:2] == [OPS_S, ROOT_S]
    assert local_path.count(ROOT_S) == 1
    assert local_path.count(OPS_S) == 1


def test_prepend_sys_path_is_idempotent(isolated_path_list):
    local_path = isolated_path_list
    assert prepend_sys_path(PROJECT_ROOT, local_path) is True
    assert prepend_sys_path(PROJECT_ROOT, local_path) is False
    assert local_path == [ROOT_S, "seed"]


@pytest.mark.parametrize(
    ("seed_path", "must_keep", "must_remove"),
    [
        (["", ".", ROOT_S, "seed"], [""], ["."]),
        ([str(PROJECT_ROOT / "tests" / ".."), "seed"], [], [str(PROJECT_ROOT / "tests" / "..")]),
    ],
)
def test_prepend_sys_path_edge_case_table(seed_path, must_keep, must_remove):
    local_path = list(seed_path)
    assert prepend_sys_path(PROJECT_ROOT, local_path) is True
    assert local_path[0] == ROOT_S
    assert local_path.count(ROOT_S) == 1
    for path in must_keep:
        assert path in local_path
    for path in must_remove:
        assert path not in local_path


def test_prepend_sys_path_dedups_symlink_equivalent(tmp_path):
    real_dir = tmp_path / "real-root"
    symlink_dir = tmp_path / "real-link"
    real_dir.mkdir()
    try:
        symlink_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Environment does not allow creating directory symlinks")

    local_path = [str(symlink_dir), "seed"]
    assert prepend_sys_path(real_dir, local_path) is True
    assert local_path[0] == str(real_dir.resolve())
    assert str(symlink_dir) not in local_path
    assert local_path == [str(real_dir.resolve()), "seed"]


def test_prepend_sys_path_case_variant_behavior_is_platform_dependent(tmp_path):
    target = tmp_path / "CaseProbe"
    target.mkdir()
    case_variant = Path(str(target).swapcase())
    local_path = [str(case_variant), "seed"]

    assert prepend_sys_path(target, local_path) is True
    assert local_path[0] == str(target.resolve())

    case_insensitive_fs = case_variant.exists()
    if case_insensitive_fs:
        assert str(case_variant) not in local_path
    else:
        assert str(case_variant) in local_path


@pytest.mark.parametrize(
    "tail",
    [
        [ROOT_S, "another"],
        ["another", ROOT_S, "more", ROOT_S],
    ],
)
def test_prepend_sys_path_moves_existing_item_to_front(isolated_path_list, tail):
    target = ROOT_S
    local_path = isolated_path_list + tail
    assert prepend_sys_path(PROJECT_ROOT, local_path) is True
    assert local_path[0] == target
    assert local_path.count(target) == 1


def test_bootstrap_returns_expected_paths(bootstrap_paths):
    repo_root_s, ops_path_s = bootstrap_paths
    assert repo_root_s == ROOT_S
    assert ops_path_s == OPS_S


def test_bootstrap_engine_path_helper():
    local_path = ["seed", ENGINE_S]
    engine_path_s = bootstrap_engine_test_sys_path(local_path)
    assert engine_path_s == ENGINE_S
    assert local_path[0] == ENGINE_S
    assert local_path.count(ENGINE_S) == 1


def test_bootstrap_utils_path_helper():
    local_path = ["seed", UTILS_S]
    utils_path_s = bootstrap_utils_test_sys_path(local_path)
    assert utils_path_s == UTILS_S
    assert local_path[0] == UTILS_S
    assert local_path.count(UTILS_S) == 1


def test_video_ops_script_path_helper():
    assert str(video_ops_script_path()) == VIDEO_OPS_S


def test_load_video_ops_module_helper():
    module = load_video_ops_module()
    assert hasattr(module, "main")


def test_load_rules_lint_module_helper():
    module = load_rules_lint_module()
    assert hasattr(module, "main")


def test_load_module_from_repo_helper():
    module = load_module_from_repo("scripts/lint/pre-commit-engine-check.py", "pre_commit_engine_check")
    assert hasattr(module, "run_gate")


def test_load_module_from_repo_missing_file_raises_import_error():
    with pytest.raises(ImportError):
        load_module_from_repo("scripts/lint/not-a-real-script.py", "missing_module_for_test")
