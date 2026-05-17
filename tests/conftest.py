"""Shared fixtures for video-ops tests."""

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from path_bootstrap import bootstrap_test_sys_path

# Ensure project modules are importable when running plain `pytest`:
# - PROJECT_ROOT enables `scripts.*` imports.
# - scripts/ops keeps legacy `lib.*` imports used by existing tests.
PROJECT_ROOT, OPS_LIB_ROOT = bootstrap_test_sys_path()


@pytest.fixture(scope="session")
def bootstrap_paths():
    """Return normalized bootstrap paths used by test runtime."""
    return PROJECT_ROOT, OPS_LIB_ROOT


@pytest.fixture
def isolated_path_list():
    """Fresh mutable path list for bootstrap helper tests."""
    return ["seed"]


@pytest.fixture
def operator_fixture():
    """Operator name used by test fixtures. Pinned to 'kai' so tests are
    self-consistent on any client fork (LONGBRO etc.) whose own
    `data/.operators.json` registers a different operator.

    Future CI matrices can parametrize this fixture to exercise multiple
    operator names — `@pytest.fixture(params=["kai", "longbro"])`.
    """
    return "kai"


def _operator_registry_payload(operator, data_dir):
    return {
        operator: {
            "data_dir": data_dir,
            "vid_prefix": "VID",
            "idea_prefix": "IDEA",
            "production_subdir": operator,
            "label": operator.title(),
        },
    }


@pytest.fixture
def patch_operator_registry(tmp_path, operator_fixture):
    """Register ``operator_fixture`` in ``lib.config`` registries for tests that
    build their own ``tmp_path`` layout (no ``tmp_project`` needed). Lets
    ``get_operator_paths(operator_fixture)`` succeed on client forks whose real
    ``data/.operators.json`` doesn't include the fixture's operator.

    ``scripts/ops/lib/config.py`` is importable via two distinct module names
    (``lib.config`` and ``scripts.ops.lib.config`` — both roots are on
    ``sys.path``). Each import yields a separate module object with its own
    copy of ``OPERATORS`` / ``VALID_OPERATORS`` / ``DEFAULT_OPERATOR``, so
    every patch must be applied to both module paths.
    """
    data_dir = tmp_path / "data" / operator_fixture
    registry = _operator_registry_payload(operator_fixture, data_dir)
    with (
        patch("lib.config._current_operator", operator_fixture),
        patch("lib.config.DEFAULT_OPERATOR", operator_fixture),
        patch("lib.config.VALID_OPERATORS", {operator_fixture}),
        patch("lib.config.OPERATORS", registry),
        patch("scripts.ops.lib.config._current_operator", operator_fixture),
        patch("scripts.ops.lib.config.DEFAULT_OPERATOR", operator_fixture),
        patch("scripts.ops.lib.config.VALID_OPERATORS", {operator_fixture}),
        patch("scripts.ops.lib.config.OPERATORS", registry),
    ):
        yield


@pytest.fixture
def tmp_project(tmp_path, operator_fixture):
    """Create a temporary project structure with empty JSON files."""
    data_dir = tmp_path / "data" / operator_fixture
    data_dir.mkdir(parents=True)

    pipeline = {
        "_meta": {
            "version": "1.0",
            "description": "統一管線 SSoT",
            "last_updated": "2026-03-17",
            "next_idea_id": 1,
            "next_vid": 1,
        },
        "items": [],
    }
    write_sharded_pipeline(data_dir, pipeline)

    pp = {
        "_meta": {"last_updated": "2026-03-17"},
        "proven_openings": [],
        "proven_ctas": [],
        "proven_formulas": [],
        "risk_patterns": [],
    }
    (data_dir / "performance-patterns.json").write_text(
        json.dumps(pp, ensure_ascii=False), encoding="utf-8"
    )

    # Create production dirs
    (tmp_path / "03-production-line" / "02-ready-to-shoot").mkdir(parents=True)
    (tmp_path / "03-production-line" / "03-done").mkdir(parents=True)

    # Create todo files
    todo_dir = tmp_path / "00-control-center" / "todo"
    todo_dir.mkdir(parents=True)
    (todo_dir / "工作待辦.md").write_text(
        "- [ ] task1\n- [x] done1\n", encoding="utf-8"
    )
    (todo_dir / "雜事待辦.md").write_text(
        "- [ ] misc1\n- [ ] misc2\n", encoding="utf-8"
    )

    return tmp_path


@pytest.fixture
def patch_paths(tmp_project, operator_fixture):
    """Patch all config paths to point to tmp_project.

    Must patch in EVERY module that imported the constant via 'from .config import X',
    because Python copies the reference at import time. DEFAULT_OPERATOR is patched
    at lib.config so client forks whose real `data/.operators.json` lacks
    `operator_fixture` still resolve owner / path lookups against the fixture's
    operator.
    """
    data_dir = tmp_project / "data" / operator_fixture
    pipeline = data_dir / "pipeline.json"
    perf_patterns = data_dir / "performance-patterns.json"
    (data_dir / "lessons.json").write_text(
        json.dumps(
            {"schema_version": "1.0", "description": "x", "next_id": 1, "lessons": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (data_dir / "todos.json").write_text(
        json.dumps(
            {"schema_version": "1.0", "description": "x", "next_id": 1, "todos": []},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    patches = [
        patch("lib.config.PROJECT_ROOT", tmp_project),
        patch("lib.config.PIPELINE_JSON", pipeline),
        patch("lib.config.PERFORMANCE_PATTERNS_JSON", perf_patterns),
        patch("lib.config._current_operator", operator_fixture),
        patch("lib.config.DEFAULT_OPERATOR", operator_fixture),
        patch("lib.config.VALID_OPERATORS", {operator_fixture}),
        patch(
            "lib.config.OPERATORS",
            _operator_registry_payload(operator_fixture, data_dir),
        ),
        patch("scripts.ops.lib.config._current_operator", operator_fixture),
        patch("scripts.ops.lib.config.DEFAULT_OPERATOR", operator_fixture),
        patch("scripts.ops.lib.config.VALID_OPERATORS", {operator_fixture}),
        patch(
            "scripts.ops.lib.config.OPERATORS",
            _operator_registry_payload(operator_fixture, data_dir),
        ),
        patch("lib.pipeline.PROJECT_ROOT", tmp_project),
        patch("lib.validate.PROJECT_ROOT", tmp_project),
        patch("lib.auto_extract.PROJECT_ROOT", tmp_project),
        patch("lib.deviations.PROJECT_ROOT", tmp_project),
        patch("lib.config.today_str", return_value="2026-03-17"),
        patch("lib.pipeline.today_str", return_value="2026-03-17"),
        patch("lib.backfill.today_str", return_value="2026-03-17"),
        patch("lib.patterns.today_str", return_value="2026-03-17"),
        patch("lib.diagnosis.today_str", return_value="2026-03-17"),
        patch("lib.storage.today_str", return_value="2026-03-17"),
        patch("lib.todos.today_str", return_value="2026-03-17"),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield tmp_project


def write_sharded_pipeline(data_dir, data, write_legacy=False):
    """Write pipeline test fixture in sharded layout.

    ``data_dir`` is an operator/template data directory (for example
    ``tmp/data/kai``). Legacy pipeline.json is optional and only used by tests
    that explicitly exercise backward-compat behaviour.
    """
    data_dir = Path(data_dir)
    items_dir = data_dir / "pipeline" / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    for old in items_dir.glob("*.json"):
        old.unlink()
    (data_dir / "pipeline" / "_meta.json").write_text(
        json.dumps(data.get("_meta", {}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for idx, item in enumerate(data.get("items", []), start=1):
        item = dict(item)
        if not item.get("idea_id"):
            item["idea_id"] = f"IDEA-{idx:03d}"
        key = item.get("vid") or item.get("idea_id") or f"item-{idx:03d}"
        (items_dir / f"{key}.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if write_legacy:
        (data_dir / "pipeline.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def make_video(
    vid="VID-001",
    topic="測試主題",
    tag="測試",
    status="待拍",
    created_date="2026-03-01",
    publish_date="",
    source="pipeline",
    script_path=None,
    script_status=None,
    source_inspiration="test",
    skill_used="flow-operator",
    title="測試標題",
    notes=None,
    backfill=None,
    transcript=None,
    learning=None,
    backfill_due_date=None,
    source_idea_id=None,
):
    """Helper to create a video dict (pipeline format: uses 'tags' not 'tag')."""
    return {
        "vid": vid,
        "topic": topic,
        "tags": tag,
        "status": status,
        "created_date": created_date,
        "status_history": [{"status": status, "date": created_date}],
        "publish_date": publish_date,
        "script_path": script_path,
        "source_inspiration": source_inspiration,
        "notes": notes,
        "backfill": backfill,
        "source": source,
        "script_status": script_status,
        "title": title,
        "skill_used": skill_used,
        "transcript": transcript,
        "learning": learning,
        "backfill_due_date": backfill_due_date,
        "source_idea_id": source_idea_id,
    }


def empty_video_data():
    """Helper to create empty video-tracking structure."""
    return {"_meta": {"last_updated": "2026-03-17"}, "videos": []}


def empty_patterns():
    """Helper to create empty performance-patterns structure."""
    return {
        "_meta": {"last_updated": "2026-03-17"},
        "proven_openings": [],
        "proven_ctas": [],
        "proven_formulas": [],
        "risk_patterns": [],
    }
