import json
import subprocess
from pathlib import Path

from timeouts import PROCESS_TIMEOUT_SEC


def _run_bootstrap(script: Path, tmp_path: Path, operator: str = "test_op", brand: str = "Test Brand"):
    cmd = ["bash", str(script), operator, brand]
    try:
        result = subprocess.run(
            cmd,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=PROCESS_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            "bootstrap-client.sh timeout"
            f"\ncmd={cmd}"
            f"\ntimeout_sec={PROCESS_TIMEOUT_SEC}"
            f"\nstdout:\n{exc.stdout or ''}"
            f"\nstderr:\n{exc.stderr or ''}"
        ) from exc
    assert result.returncode == 0, (
        "bootstrap-client.sh failed"
        f"\nexit_code={result.returncode}"
        f"\nstdout:\n{result.stdout}"
        f"\nstderr:\n{result.stderr}"
    )
    return result


def _seed_repo(tmp_path: Path):
    (tmp_path / "scripts" / "bootstrap").mkdir(parents=True)
    (tmp_path / "data" / "template").mkdir(parents=True)
    (tmp_path / "data" / "kai").mkdir(parents=True)
    (tmp_path / "01-data-brain" / "template").mkdir(parents=True)
    (tmp_path / "03-production-line" / "02-ready-to-shoot").mkdir(parents=True)
    (tmp_path / "03-production-line" / "03-done").mkdir(parents=True)

    repo_root = Path(__file__).resolve().parents[1]
    for rel in ("scripts/bootstrap/bootstrap-client.sh", "scripts/bootstrap/reset-operator.py"):
        (tmp_path / rel).write_text((repo_root / rel).read_text(encoding="utf-8"), encoding="utf-8")

    (tmp_path / "data" / "template" / "pipeline.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "pipeline" / "items").mkdir(parents=True)
    (tmp_path / "data" / "template" / "pipeline" / "_meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "todos.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "lessons.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "performance-patterns.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "hardening-archive.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "brand-monitor.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "social-followers.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "template" / "topic-history.json").write_text("{}", encoding="utf-8")
    (tmp_path / "01-data-brain" / "template" / "brand.md").write_text("# brand", encoding="utf-8")
    (tmp_path / "01-data-brain" / "template" / "cases.md").write_text("# cases", encoding="utf-8")
    (tmp_path / "engine-manifest.json").write_text(
        json.dumps({"_meta": {"engine_version": "4.51"}, "files": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("Red Tea Bus", encoding="utf-8")
    (tmp_path / "data" / "kai" / "pipeline.json").write_text("{\"kai\":1}", encoding="utf-8")


def test_bootstrap_client_smoke_and_idempotent(tmp_path):
    _seed_repo(tmp_path)
    script = tmp_path / "scripts" / "bootstrap" / "bootstrap-client.sh"

    first = _run_bootstrap(script, tmp_path)
    assert "bootstrap 完成" in first.stdout
    assert (tmp_path / "data" / "test_op" / "pipeline.json").exists()
    assert (tmp_path / "data" / "test_op" / "pipeline" / "_meta.json").exists()
    assert (tmp_path / "data" / "test_op" / "pipeline" / "items").is_dir()
    assert (tmp_path / "data" / "test_op" / "todos.json").exists()
    assert (tmp_path / "data" / "test_op" / "lessons.json").exists()
    assert (tmp_path / "data" / "test_op" / "performance-patterns.json").exists()
    assert (tmp_path / "data" / "test_op" / "hardening-archive.json").exists()
    assert (tmp_path / "data" / "kai" / "pipeline.json").read_text(encoding="utf-8") == "{\"kai\":1}"

    operators = json.loads((tmp_path / "data" / ".operators.json").read_text(encoding="utf-8"))
    assert "test_op" in operators["operators"]

    second = _run_bootstrap(script, tmp_path)
    assert "已存在，跳過" in second.stdout
    operators2 = json.loads((tmp_path / "data" / ".operators.json").read_text(encoding="utf-8"))
    assert list(operators2["operators"].keys()).count("test_op") == 1


def test_bootstrap_copies_all_data_brain_templates(tmp_path):
    _seed_repo(tmp_path)
    script = tmp_path / "scripts" / "bootstrap" / "bootstrap-client.sh"
    _run_bootstrap(script, tmp_path)

    brain_template = tmp_path / "01-data-brain" / "template"
    brain_root = tmp_path / "01-data-brain"
    for template_file in brain_template.glob("*.md"):
        if template_file.name == "CLAUDE.local.md":
            continue
        expected = brain_root / template_file.name
        assert expected.exists(), f"bootstrap 未複製 {template_file.name} 到 01-data-brain/"


def test_bootstrap_copies_extended_data_templates(tmp_path):
    """v5.55+：驗證 brand-monitor / social-followers / topic-history 也被 copy 到新 operator。"""
    _seed_repo(tmp_path)
    script = tmp_path / "scripts" / "bootstrap" / "bootstrap-client.sh"
    _run_bootstrap(script, tmp_path)

    operator_data = tmp_path / "data" / "test_op"
    for filename in ("brand-monitor.json", "social-followers.json", "topic-history.json"):
        expected = operator_data / filename
        assert expected.exists(), f"bootstrap 未複製 {filename} 到 data/test_op/"
