"""Tests for scripts/utils/wipe_client.py — short-term template reset.

Destructive operation, so tests focus on the gather/filter logic that
determines what gets preserved vs deleted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "utils"))
from wipe_client import (  # noqa: E402
    PRESERVE_FILENAMES,
    filter_lessons,
    gather_files_to_clear,
    get_archive_count,
)


class TestFilterLessons:
    def test_drops_soft_lessons(self):
        data = {"lessons": [{"id": "L-1", "stage": "soft", "pattern": "x"}]}
        kept, dropped = filter_lessons(data, "alex", "")
        assert kept == 0
        assert len(dropped) == 1
        assert dropped[0]["reason"] == "stage != hardened"

    def test_drops_archived_lessons(self):
        data = {"lessons": [{"id": "L-1", "stage": "archived", "pattern": "x"}]}
        kept, dropped = filter_lessons(data, "alex", "")
        assert kept == 0
        assert dropped[0]["reason"] == "stage != hardened"

    def test_keeps_hardened_engine_lessons(self):
        data = {
            "lessons": [
                {
                    "id": "L-1",
                    "stage": "hardened",
                    "pattern": "engine-wide refactor checklist",
                    "counter_pattern": "always update CHANGELOG",
                }
            ]
        }
        kept, dropped = filter_lessons(data, "alex", "Aurora")
        assert kept == 1
        assert dropped == []
        assert data["lessons"][0]["id"] == "L-1"

    def test_drops_hardened_with_operator_keyword(self):
        data = {
            "lessons": [
                {
                    "id": "L-1",
                    "stage": "hardened",
                    "pattern": "alex 的特殊習慣",
                    "counter_pattern": "",
                }
            ]
        }
        kept, dropped = filter_lessons(data, "alex", "")
        assert kept == 0
        assert "alex" in dropped[0]["reason"]

    def test_drops_hardened_with_brand_keyword(self):
        data = {
            "lessons": [
                {
                    "id": "L-1",
                    "stage": "hardened",
                    "pattern": "Aurora 品牌限定模式",
                    "counter_pattern": "",
                }
            ]
        }
        kept, dropped = filter_lessons(data, "alex", "Aurora")
        assert kept == 0
        assert dropped[0]["reason"].lower().find("aurora") != -1

    def test_brand_keyword_case_insensitive(self):
        data = {
            "lessons": [
                {
                    "id": "L-1",
                    "stage": "hardened",
                    "pattern": "AURORA 全大寫",
                    "counter_pattern": "",
                }
            ]
        }
        kept, _ = filter_lessons(data, "alex", "Aurora")
        assert kept == 0

    def test_ignores_title_field(self):
        """Regression: 'title' is not in lessons schema; should not affect filter."""
        data = {
            "lessons": [
                {
                    "id": "L-1",
                    "stage": "hardened",
                    "pattern": "generic",
                    "counter_pattern": "generic",
                    "title": "alex special",  # field doesn't exist in schema
                }
            ]
        }
        kept, _ = filter_lessons(data, "alex", "")
        assert kept == 1  # title field ignored, lesson preserved

    def test_empty_brand_name_skips_brand_filter(self):
        data = {
            "lessons": [
                {
                    "id": "L-1",
                    "stage": "hardened",
                    "pattern": "talks about aurora",
                    "counter_pattern": "",
                }
            ]
        }
        kept, _ = filter_lessons(data, "alex", "")
        assert kept == 1

    def test_non_dict_input(self):
        kept, dropped = filter_lessons([], "alex", "")
        assert kept == 0
        assert dropped == []


class TestGetArchiveCount:
    def test_missing_file(self, tmp_path):
        assert get_archive_count(tmp_path, "alex") == 0

    def test_canonical_items_key(self, tmp_path):
        d = tmp_path / "data" / "alex"
        d.mkdir(parents=True)
        (d / "hardening-archive.json").write_text(
            json.dumps({"items": [{"id": 1}, {"id": 2}, {"id": 3}]}),
            encoding="utf-8",
        )
        assert get_archive_count(tmp_path, "alex") == 3

    def test_empty_items(self, tmp_path):
        d = tmp_path / "data" / "alex"
        d.mkdir(parents=True)
        (d / "hardening-archive.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )
        assert get_archive_count(tmp_path, "alex") == 0

    def test_corrupt_json_returns_zero(self, tmp_path, capsys):
        d = tmp_path / "data" / "alex"
        d.mkdir(parents=True)
        (d / "hardening-archive.json").write_text("{not json", encoding="utf-8")
        assert get_archive_count(tmp_path, "alex") == 0
        captured = capsys.readouterr()
        assert "parse failed" in captured.err

    def test_non_canonical_schema_returns_zero(self, tmp_path):
        """Old fallback keys (entries/records/archive) are no longer honored."""
        d = tmp_path / "data" / "alex"
        d.mkdir(parents=True)
        (d / "hardening-archive.json").write_text(
            json.dumps({"entries": [{"id": 1}]}), encoding="utf-8"
        )
        assert get_archive_count(tmp_path, "alex") == 0


class TestGatherFilesToClear:
    def _setup_repo(self, tmp_path):
        """Build minimal project structure matching wipe_client expectations."""
        (tmp_path / "01-data-brain").mkdir()
        (tmp_path / "01-data-brain" / "transcripts").mkdir()
        (tmp_path / "01-data-brain" / "personas").mkdir()
        (tmp_path / "03-production-line" / "02-ready-to-shoot").mkdir(parents=True)
        (tmp_path / "03-production-line" / "03-done").mkdir()
        (tmp_path / "00-control-center").mkdir()
        (tmp_path / "data" / "alex").mkdir(parents=True)
        return tmp_path

    def test_preserves_readme_in_root_dirs_delete(self, tmp_path):
        repo = self._setup_repo(tmp_path)
        # 00-control-center is in ROOT_DIRS_DELETE
        (repo / "00-control-center" / "README.md").write_text(
            "keep me", encoding="utf-8"
        )
        (repo / "00-control-center" / "notes.md").write_text(
            "delete me", encoding="utf-8"
        )

        items = gather_files_to_clear(repo, "alex")
        paths = {item["path"] for item in items}

        # README.md should NOT appear in the gather list (preserved)
        assert "00-control-center/README.md" not in paths
        assert "00-control-center/notes.md" in paths

    def test_preserves_gitkeep_in_transcripts(self, tmp_path):
        repo = self._setup_repo(tmp_path)
        (repo / "01-data-brain" / "transcripts" / ".gitkeep").write_text(
            "", encoding="utf-8"
        )
        (repo / "01-data-brain" / "transcripts" / "voice-2026-05-21.md").write_text(
            "transcript content", encoding="utf-8"
        )

        items = gather_files_to_clear(repo, "alex")
        paths = {item["path"] for item in items}

        assert "01-data-brain/transcripts/.gitkeep" not in paths
        assert "01-data-brain/transcripts/voice-2026-05-21.md" in paths

    def test_includes_brand_md_when_present(self, tmp_path):
        repo = self._setup_repo(tmp_path)
        (repo / "01-data-brain" / "brand.md").write_text("# Brand", encoding="utf-8")

        items = gather_files_to_clear(repo, "alex")
        actions = {item["path"]: item["action"] for item in items}

        assert actions.get("01-data-brain/brand.md") == "reset-from-template"

    def test_action_categories(self, tmp_path):
        repo = self._setup_repo(tmp_path)
        (repo / "01-data-brain" / "brand.md").write_text("x", encoding="utf-8")
        (repo / "01-data-brain" / "brand-summary.md").write_text("x", encoding="utf-8")
        (repo / "01-data-brain" / "transcripts" / "a.md").write_text(
            "x", encoding="utf-8"
        )

        items = gather_files_to_clear(repo, "alex")
        actions = {item["path"]: item["action"] for item in items}

        assert actions["01-data-brain/brand.md"] == "reset-from-template"
        assert actions["01-data-brain/brand-summary.md"] == "delete"
        assert actions["01-data-brain/transcripts/a.md"] == "delete"


class TestPreserveFilenames:
    """Sanity check that the preserve set covers expected structural files."""

    def test_includes_readme(self):
        assert "README.md" in PRESERVE_FILENAMES

    def test_includes_gitkeep(self):
        assert ".gitkeep" in PRESERVE_FILENAMES
