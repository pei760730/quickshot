import json
from pathlib import Path

import pytest

from lib import config


def test_load_operators_from_file(tmp_path, monkeypatch):
    operators_file = tmp_path / ".operators.json"
    operators_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "operators": {
                    "kai": {
                        "display_name": "Kai",
                        "data_dir_rel": "data/kai",
                        "enabled": True,
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config, "_OPERATORS_JSON", operators_file)
    loaded = config._load_operators()
    assert "kai" in loaded
    assert loaded["kai"]["data_dir"] == Path(tmp_path / "data" / "kai")


def test_load_operators_fallback_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config, "_OPERATORS_JSON", tmp_path / "not-exists.json")
    loaded = config._load_operators()
    assert "kai" in loaded


def test_load_operators_raise_on_invalid_schema(tmp_path, monkeypatch):
    operators_file = tmp_path / ".operators.json"
    operators_file.write_text(json.dumps({"schema_version": "1.0", "operators": {"kai": {}}}), encoding="utf-8")
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config, "_OPERATORS_JSON", operators_file)
    with pytest.raises(ValueError, match="data_dir_rel"):
        config._load_operators()
