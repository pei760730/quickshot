"""Tests for lib/sedimentation.py — 回填後歷史脈絡組裝（v5.x「縮」後）。

v5.x 移除自動提案（propose_rules_from_verifier / apply_proposed_rule、跨時間
自我進化機器）。本模組只保留 get_sedimentation_context（供 Claude 手動判斷是否
記 lesson）+ generation rules 載入。
"""

from lib.sedimentation import (
    load_generation_rules,
    save_generation_rules,
    get_sedimentation_context,
)
from lib.lessons import add_lesson


class TestLoadGenerationRules:
    def test_load_rules_includes_manual_and_graduated_mistake(
        self, patch_paths, operator_fixture
    ):
        add_lesson(
            operator_fixture,
            "manual",
            "m1",
            counter_pattern="r1",
            stage="soft",
            scope=[],
        )
        add_lesson(
            operator_fixture,
            "graduated_mistake",
            "m2",
            counter_pattern="r2",
            stage="soft",
            scope=[],
        )
        patterns = {r["pattern"] for r in load_generation_rules()["avoid_patterns"]}
        assert "m1" in patterns
        assert "m2" in patterns


class TestGetSedimentationContext:
    def test_returns_structured_context(self, patch_paths, operator_fixture):
        from lib.storage import save_json
        from pathlib import Path

        root = Path(patch_paths)
        save_json(
            root / "data" / operator_fixture / "performance-patterns.json",
            {
                "_meta": {"last_updated": "2026-03-17"},
                "risk_patterns": [{"pattern": "開場太慢", "count": 3}],
                "proven_openings": [],
                "proven_ctas": [],
                "proven_formulas": [],
            },
            update_meta=False,
        )
        add_lesson(operator_fixture, "mistake", "active", stage="soft", scope=[])
        add_lesson(operator_fixture, "mistake", "done", stage="hardened", scope=[])
        save_generation_rules(
            {
                "description": "x",
                "avoid_patterns": [
                    {"pattern": "p1", "rule": "r1", "source": "verifier"}
                ],
            }
        )

        items = [
            {
                "vid": "VID-001",
                "topic": "A",
                "hook_type": "B2",
                "version": "B2",
                "backfill": {"backfilled_date": "2026-03-17"},
            },
            {
                "vid": "VID-002",
                "topic": "B",
                "hook_type": "B2",
                "version": "B2",
                "backfill": {"backfilled_date": "2026-03-16"},
            },
        ]
        ctx = get_sedimentation_context(items, "VID-001", operator=operator_fixture)
        assert ctx["vid"] == "VID-001"
        assert len(ctx["recent_similar_videos"]) == 1
        assert len(ctx["avoid_patterns"]) == 1
        assert len(ctx["risk_patterns"]) == 1
        assert len(ctx["ungraduated_mistakes"]) == 1
        assert ctx["limits"]["max_proposals"] == 2

    def test_context_uses_meta_max_proposals(self, patch_paths, operator_fixture):
        items = [{"vid": "VID-001", "topic": "A", "hook_type": "B2"}]
        ctx = get_sedimentation_context(
            items,
            "VID-001",
            operator=operator_fixture,
            meta={"sedimentation": {"max_proposals_per_backfill": 5}},
        )
        assert ctx["limits"]["max_proposals"] == 5
