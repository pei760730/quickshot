"""Tests for scripts/ops/lib/health.py — brain health per-dimension snapshot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ops"))
from lib.health import (
    compute_brand_health,
    compute_cases_health,
    compute_health,
    compute_lessons_health,
    compute_operators_health,
    compute_patterns_health,
    compute_personas_health,
    compute_pipeline_health,
    compute_todos_health,
    compute_transcripts_health,
    format_health_report,
)


@pytest.fixture
def fake_repo(tmp_path):
    """Build a minimal fake repo layout under tmp_path."""
    brain = tmp_path / "01-data-brain"
    (brain / "personas").mkdir(parents=True)
    (brain / "transcripts").mkdir()
    (tmp_path / "data").mkdir()
    return tmp_path


def _write_brand_md(repo, sections):
    """sections: list of (key, name, last_updated_value).

    last_updated_value="" → unfilled. last_updated_value="2026-05-18" → filled.
    """
    parts = ["# Test Brand 品牌知識", ""]
    for key, name, lu in sections:
        parts.append(f"## {key} {name}")
        parts.append(f"<!-- last_updated: {lu} -->")
        parts.append("")
        parts.append("body")
        parts.append("")
    (repo / "01-data-brain" / "brand.md").write_text("\n".join(parts), encoding="utf-8")


class TestBrandHealth:
    def test_missing_file_returns_none(self, tmp_path):
        assert compute_brand_health(tmp_path / "nope.md") is None

    def test_empty_sections(self, fake_repo):
        (fake_repo / "01-data-brain" / "brand.md").write_text(
            "# Empty\n", encoding="utf-8"
        )
        h = compute_brand_health(fake_repo / "01-data-brain" / "brand.md")
        assert h.sections_total == 0
        assert h.sections_filled == 0
        assert h.mvp_filled == 0
        assert h.missing_mvp == []
        assert h.template_placeholder_present is False

    def test_partial_mvp_fill(self, fake_repo):
        _write_brand_md(
            fake_repo,
            [
                ("[0]", "基本資料", "2026-05-18"),
                ("[1]", "核心專長", "2026-05-18"),
                ("[2]", "受眾", ""),
                ("[2.5]", "高流量素材庫", ""),
                ("[3]", "說話風格", ""),
                ("[5]", "禁忌", ""),
            ],
        )
        h = compute_brand_health(fake_repo / "01-data-brain" / "brand.md")
        assert h.sections_total == 6
        assert h.sections_filled == 2
        assert h.mvp_filled == 2  # [0] and [1] are MVP and filled
        # Missing: [2.5], [3], [5] (MVP, unfilled). [2] is not MVP.
        missing_keys = {m.split()[0] for m in h.missing_mvp}
        assert missing_keys == {"[2.5]", "[3]", "[5]"}

    def test_all_mvp_filled(self, fake_repo):
        _write_brand_md(
            fake_repo,
            [
                ("[0]", "基本資料", "2026-05-18"),
                ("[1]", "核心專長", "2026-05-18"),
                ("[2.5]", "素材", "2026-05-18"),
                ("[3]", "調性", "2026-05-18"),
                ("[5]", "禁忌", "2026-05-18"),
            ],
        )
        h = compute_brand_health(fake_repo / "01-data-brain" / "brand.md")
        assert h.mvp_filled == 5
        assert h.missing_mvp == []

    def test_template_placeholder_detected(self, fake_repo):
        (fake_repo / "01-data-brain" / "brand.md").write_text(
            "# {{BRAND_NAME}} 品牌\n", encoding="utf-8"
        )
        h = compute_brand_health(fake_repo / "01-data-brain" / "brand.md")
        assert h.template_placeholder_present is True


class TestCasesHealth:
    def test_missing_file_returns_none(self, tmp_path):
        assert compute_cases_health(tmp_path / "nope.md") is None

    def test_count_filled_cases(self, fake_repo):
        text = (
            "# Cases\n\n"
            "## [S1] 起源\n<!-- last_updated: 2026-05-18 -->\nbody\n\n"
            "## [S2] 慘\n<!-- last_updated: -->\nbody\n\n"
            "## [S3] 高峰\n<!-- last_updated: 2026-05-18 -->\nbody\n"
        )
        (fake_repo / "01-data-brain" / "cases.md").write_text(text, encoding="utf-8")
        h = compute_cases_health(fake_repo / "01-data-brain" / "cases.md")
        assert h.cases_total == 3
        assert h.cases_filled == 2


class TestPersonasHealth:
    def test_no_personas_dir(self, tmp_path):
        # tmp_path with no 01-data-brain/personas dir
        (tmp_path / "01-data-brain").mkdir()
        h = compute_personas_health(tmp_path, "default")
        assert h.files_present == []
        assert h.primary_present is False
        assert h.partner_present is False
        # fallback filenames
        assert h.primary_file == "kai.md"
        assert h.partner_file == "an.md"

    def test_fallback_filenames(self, fake_repo):
        (fake_repo / "01-data-brain" / "personas" / "kai.md").write_text(
            "primary content x", encoding="utf-8"
        )
        h = compute_personas_health(fake_repo, "default")
        assert h.primary_file == "kai.md"
        assert h.primary_present is True
        assert h.partner_present is False
        assert ("kai.md", len("primary content x")) in h.files_present

    def test_operator_keyed_filenames(self, fake_repo):
        (fake_repo / "01-data-brain" / "personas" / "alex.md").write_text(
            "alex content", encoding="utf-8"
        )
        ops = {
            "schema_version": "1.0",
            "operators": {
                "alex": {
                    "data_dir_rel": "data/alex",
                    "primary_persona_file": "alex.md",
                    "partner_persona_file": "sam.md",
                }
            },
        }
        (fake_repo / "data" / ".operators.json").write_text(
            json.dumps(ops), encoding="utf-8"
        )
        h = compute_personas_health(fake_repo, "alex")
        assert h.primary_file == "alex.md"
        assert h.primary_present is True
        assert h.partner_file == "sam.md"
        assert h.partner_present is False


class TestOperatorsHealth:
    def test_missing_file(self, tmp_path):
        h = compute_operators_health(tmp_path / "nope.json")
        assert h.total_enabled == 0
        assert h.operator_keys == []

    def test_filters_disabled(self, fake_repo):
        ops = {
            "schema_version": "1.0",
            "operators": {
                "a": {"data_dir_rel": "data/a", "enabled": True},
                "b": {"data_dir_rel": "data/b", "enabled": False},
                "c": {"data_dir_rel": "data/c"},  # default enabled=True
            },
        }
        path = fake_repo / "data" / ".operators.json"
        path.write_text(json.dumps(ops), encoding="utf-8")
        h = compute_operators_health(path)
        assert h.total_enabled == 2
        assert h.operator_keys == ["a", "c"]

    def test_corrupt_json(self, tmp_path):
        p = tmp_path / "ops.json"
        p.write_text("{not json", encoding="utf-8")
        h = compute_operators_health(p)
        assert h.total_enabled == 0


class TestPipelineHealth:
    def test_missing(self, tmp_path):
        h = compute_pipeline_health(tmp_path / "no-such-dir")
        assert h.items_total == 0
        assert h.by_status == {}

    def test_status_counts(self, tmp_path):
        d = tmp_path / "op"
        items_dir = d / "pipeline" / "items"
        items_dir.mkdir(parents=True)
        for i, status in enumerate(["inbox", "已上線", "已上線", "剪輯中"]):
            (items_dir / f"item-{i}.json").write_text(
                json.dumps({"status": status}), encoding="utf-8"
            )
        h = compute_pipeline_health(d)
        assert h.items_total == 4
        assert h.by_status == {"inbox": 1, "已上線": 2, "剪輯中": 1}


class TestLessonsHealth:
    def test_empty(self, tmp_path):
        h = compute_lessons_health(tmp_path)
        assert h.soft == 0 and h.hardened == 0 and h.archived == 0

    def test_stage_counts(self, tmp_path):
        d = tmp_path / "op"
        d.mkdir()
        data = {
            "lessons": [
                {"stage": "soft"},
                {"stage": "soft"},
                {"stage": "hardened"},
                {"stage": "archived"},
                {"stage": "unknown-bad"},  # not counted
            ]
        }
        (d / "lessons.json").write_text(json.dumps(data), encoding="utf-8")
        h = compute_lessons_health(d)
        assert h.soft == 2
        assert h.hardened == 1
        assert h.archived == 1


class TestTodosHealth:
    def test_open_counts(self, tmp_path):
        d = tmp_path / "op"
        d.mkdir()
        data = {
            "todos": [
                {"state": "pending"},
                {"state": "pending"},
                {"state": "in_progress"},
                {"state": "closed"},
            ]
        }
        (d / "todos.json").write_text(json.dumps(data), encoding="utf-8")
        h = compute_todos_health(d)
        assert h.pending == 2
        assert h.in_progress == 1
        assert h.closed == 1
        assert h.open == 3


class TestPatternsHealth:
    def test_empty(self, tmp_path):
        h = compute_patterns_health(tmp_path)
        assert h.proven_openings == 0
        assert h.proven_ctas == 0

    def test_counts(self, tmp_path):
        d = tmp_path / "op"
        d.mkdir()
        data = {
            "proven_openings": [{"x": 1}, {"x": 2}],
            "proven_ctas": [{"x": 1}],
            "proven_formulas": [],
            "risk_patterns": [{"x": 1}, {"x": 2}, {"x": 3}],
        }
        (d / "performance-patterns.json").write_text(json.dumps(data), encoding="utf-8")
        h = compute_patterns_health(d)
        assert h.proven_openings == 2
        assert h.proven_ctas == 1
        assert h.proven_formulas == 0
        assert h.risk_patterns == 3


class TestTranscriptsHealth:
    def test_empty(self, tmp_path):
        h = compute_transcripts_health(tmp_path)
        assert h.files == 0

    def test_count_md_files(self, fake_repo):
        d = fake_repo / "01-data-brain" / "transcripts"
        (d / "a.md").write_text("x", encoding="utf-8")
        (d / "b.md").write_text("x", encoding="utf-8")
        (d / "ignore.txt").write_text("x", encoding="utf-8")
        h = compute_transcripts_health(fake_repo)
        assert h.files == 2


class TestComputeHealthIntegration:
    def test_full_brain_health(self, fake_repo):
        _write_brand_md(
            fake_repo,
            [
                ("[0]", "基本資料", "2026-05-18"),
                ("[1]", "核心專長", ""),
                ("[2.5]", "素材", "2026-05-18"),
                ("[3]", "調性", ""),
                ("[5]", "禁忌", ""),
            ],
        )
        (fake_repo / "01-data-brain" / "cases.md").write_text(
            "## [S1] 起源\n<!-- last_updated: 2026-05-18 -->\n", encoding="utf-8"
        )
        (fake_repo / "01-data-brain" / "personas" / "kai.md").write_text(
            "x", encoding="utf-8"
        )
        ops = {
            "schema_version": "1.0",
            "operators": {"default": {"data_dir_rel": "data/default"}},
        }
        (fake_repo / "data" / ".operators.json").write_text(
            json.dumps(ops), encoding="utf-8"
        )
        h = compute_health("default", root=fake_repo)
        assert h.operator == "default"
        assert h.brand.mvp_filled == 2
        assert h.cases.cases_filled == 1
        assert h.personas.primary_present is True
        assert h.operators.total_enabled == 1

    def test_format_report_renders_without_error(self, fake_repo):
        h = compute_health("default", root=fake_repo)
        report = format_health_report(h)
        assert "🧠 大腦健康度" in report
        assert "operator=default" in report
