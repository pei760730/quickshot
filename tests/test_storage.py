"""Tests for lib/storage.py — load_json + save_json atomic I/O."""

import json
from unittest.mock import patch

import pytest


class TestLoadJson:
    """Test load_json: missing file, valid file, corrupted file."""

    def test_missing_file_returns_empty(self, tmp_path):
        from lib.storage import load_json
        result = load_json(tmp_path / "nonexistent.json", {"items": []})
        assert result == {"items": []}

    def test_valid_file(self, tmp_path):
        from lib.storage import load_json
        f = tmp_path / "data.json"
        f.write_text('{"videos": [1, 2]}', encoding="utf-8")
        result = load_json(f, {"videos": []})
        assert result == {"videos": [1, 2]}

    def test_corrupted_file_exits(self, tmp_path):
        from lib.storage import load_json
        f = tmp_path / "bad.json"
        f.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(SystemExit):
            load_json(f, {"videos": []})

    def test_empty_file_exits(self, tmp_path):
        from lib.storage import load_json
        f = tmp_path / "empty.json"
        f.write_text("", encoding="utf-8")
        with pytest.raises(SystemExit):
            load_json(f, {"videos": []})


class TestSaveJson:
    """Test save_json: atomic write, meta update, cleanup on error."""

    def test_basic_write(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "out.json"
        data = {"_meta": {"last_updated": ""}, "items": [1, 2]}
        with patch("lib.storage.today_str", return_value="2026-03-20"):
            save_json(f, data)
        result = json.loads(f.read_text(encoding="utf-8"))
        assert result["items"] == [1, 2]
        assert result["_meta"]["last_updated"] == "2026-03-20"

    def test_meta_update_disabled(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "out.json"
        data = {"_meta": {"last_updated": "old"}, "items": []}
        save_json(f, data, update_meta=False)
        result = json.loads(f.read_text(encoding="utf-8"))
        assert result["_meta"]["last_updated"] == "old"

    def test_no_meta_key(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "out.json"
        data = {"items": [1]}
        save_json(f, data)
        result = json.loads(f.read_text(encoding="utf-8"))
        assert result == {"items": [1]}

    def test_overwrite_existing(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "out.json"
        f.write_text('{"old": true}', encoding="utf-8")
        with patch("lib.storage.today_str", return_value="2026-03-20"):
            save_json(f, {"_meta": {"last_updated": ""}, "new": True})
        result = json.loads(f.read_text(encoding="utf-8"))
        assert "new" in result
        assert "old" not in result

    def test_creates_parent_dirs(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "sub" / "dir" / "out.json"
        save_json(f, {"x": 1})
        assert f.exists()

    def test_unicode_content(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "out.json"
        data = {"title": "加盟割韭菜", "items": ["中文測試"]}
        save_json(f, data)
        result = json.loads(f.read_text(encoding="utf-8"))
        assert result["title"] == "加盟割韭菜"

    def test_no_leftover_tmp_on_success(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "out.json"
        save_json(f, {"x": 1})
        tmp_files = list(tmp_path.glob(".*_*.tmp"))
        assert len(tmp_files) == 0

    def test_lock_file_created(self, tmp_path):
        from lib.storage import save_json
        f = tmp_path / "data.json"
        save_json(f, {"x": 1})
        lock = tmp_path / ".data.lock"
        assert lock.exists()
