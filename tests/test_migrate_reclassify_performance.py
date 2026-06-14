"""Tests for scripts/ops/migrate_reclassify_performance.py."""

import importlib.util
import json
from pathlib import Path


def _load_migration_module():
    repo_root = Path(__file__).resolve().parent.parent
    mod_path = repo_root / "scripts" / "ops" / "migrate_reclassify_performance.py"
    spec = importlib.util.spec_from_file_location("migrate_reclassify_performance", mod_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_migrate_file_dry_run_does_not_write(tmp_path):
    mod = _load_migration_module()
    pipeline = tmp_path / "pipeline.json"
    payload = {
        "items": [
            {
                "vid": "VID-001",
                "backfill": {
                    "views": 1000,
                    "retention_3s": 38.0,
                    "completion_rate": 44.35,
                    "performance": "normal",
                },
            }
        ]
    }
    pipeline.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    before = pipeline.read_text(encoding="utf-8")

    result = mod.migrate_file(pipeline, apply=False)
    assert len(result["changes"]) == 1
    assert result["changes"][0]["before"] == "normal"
    assert result["changes"][0]["after"] == "low"
    assert pipeline.read_text(encoding="utf-8") == before


def test_migrate_file_apply_updates_performance(tmp_path):
    mod = _load_migration_module()
    pipeline = tmp_path / "pipeline.json"
    payload = {
        "items": [
            {
                "vid": "VID-001",
                "backfill": {
                    "views": 1000,
                    "retention_3s": 38.0,
                    "completion_rate": 44.35,
                    "performance": "normal",
                },
            }
        ]
    }
    pipeline.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = mod.migrate_file(pipeline, apply=True)
    assert len(result["changes"]) == 1
    data = json.loads(pipeline.read_text(encoding="utf-8"))
    assert data["items"][0]["backfill"]["performance"] == "low"
