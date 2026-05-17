import re
import subprocess
import sys
from pathlib import Path

from timeouts import PROCESS_TIMEOUT_SEC


REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_TEST = "tests/test_import_bootstrap.py::test_bootstrap_paths_fixture_contract"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=PROCESS_TIMEOUT_SEC,
    )


def _passed_count(output: str) -> int:
    match = re.search(r"(\d+)\s+passed", output)
    return int(match.group(1)) if match else 0


def test_pytest_entrypoints_are_consistent():
    direct = _run(["pytest", "-q", TARGET_TEST])
    module = _run([sys.executable, "-m", "pytest", "-q", TARGET_TEST])

    assert direct.returncode == 0, direct.stdout + direct.stderr
    assert module.returncode == 0, module.stdout + module.stderr
    assert _passed_count(direct.stdout) == 1
    assert _passed_count(module.stdout) == 1
