"""Tests for lib/sedimentation.py — verifier-driven rule sedimentation."""

from lib.sedimentation import (
    propose_rules_from_verifier,
    apply_proposed_rule,
    load_generation_rules,
    save_generation_rules,
    SEDIMENTATION_THRESHOLD,
    get_sedimentation_context,
)
from lib.lessons import add_lesson


class TestProposeRulesFromVerifier:
    """Test rule proposals from accumulated verifier scores."""

    def _make_items_with_ai_residue(self, count):
        return [
            {
                "vid": f"VID-{i:03d}",
                "verifier_scores": {
                    "ai_residue_count": 2,
                    "conflict_score": 7,
                    "data_consistency": True,
                    "pass_count": "4/5",
                },
            }
            for i in range(1, count + 1)
        ]

    def _make_items_with_low_conflict(self, count):
        return [
            {
                "vid": f"VID-{i:03d}",
                "verifier_scores": {
                    "ai_residue_count": 0,
                    "conflict_score": 3,
                    "data_consistency": True,
                    "pass_count": "3/5",
                },
            }
            for i in range(1, count + 1)
        ]

    def test_no_proposals_below_threshold(self):
        items = self._make_items_with_ai_residue(SEDIMENTATION_THRESHOLD - 1)
        assert propose_rules_from_verifier(items) == []

    def test_proposes_ai_residue_rule(self, patch_paths):
        items = self._make_items_with_ai_residue(SEDIMENTATION_THRESHOLD)
        proposals = propose_rules_from_verifier(items)
        assert len(proposals) == 1
        p = proposals[0]
        assert p["issue_type"] == "ai_residue"
        assert p["count"] == SEDIMENTATION_THRESHOLD
        assert "proposed_rule" in p
        assert p["already_exists"] is False

    def test_proposes_low_conflict_rule(self, patch_paths):
        items = self._make_items_with_low_conflict(4)
        proposals = propose_rules_from_verifier(items)
        types = [p["issue_type"] for p in proposals]
        assert "low_conflict" in types

    def test_proposes_data_inconsistency_rule(self, patch_paths):
        items = [
            {
                "vid": f"VID-{i:03d}",
                "verifier_scores": {
                    "ai_residue_count": 0,
                    "conflict_score": 7,
                    "data_consistency": False,
                    "pass_count": "3/5",
                },
            }
            for i in range(1, 4)
        ]
        proposals = propose_rules_from_verifier(items)
        types = [p["issue_type"] for p in proposals]
        assert "data_inconsistency" in types

    def test_skips_items_without_verifier_scores(self):
        items = [{"vid": f"VID-{i:03d}"} for i in range(1, 10)]
        assert propose_rules_from_verifier(items) == []

    def test_multiple_proposals(self, patch_paths):
        items = self._make_items_with_ai_residue(3)
        low_items = self._make_items_with_low_conflict(3)
        for i, item in enumerate(low_items, start=4):
            item["vid"] = f"VID-{i:03d}"
        proposals = propose_rules_from_verifier(items + low_items)
        types = {p["issue_type"] for p in proposals}
        assert "ai_residue" in types
        assert "low_conflict" in types

    def test_marks_already_exists(self, patch_paths):
        save_generation_rules(
            {
                "description": "test",
                "avoid_patterns": [
                    {
                        "pattern": "存檔時 AI 味殘留反覆出現",
                        "rule": "existing rule",
                        "source": "test",
                    }
                ],
            }
        )
        items = self._make_items_with_ai_residue(3)
        proposals = propose_rules_from_verifier(items)
        ai_prop = [p for p in proposals if p["issue_type"] == "ai_residue"]
        assert len(ai_prop) == 1
        assert ai_prop[0]["already_exists"] is True

    def test_uses_meta_fallback_threshold(self, patch_paths):
        items = self._make_items_with_ai_residue(2)
        proposals = propose_rules_from_verifier(
            items,
            meta={"sedimentation": {"fallback_threshold": 2}},
        )
        assert len(proposals) == 1
        assert proposals[0]["issue_type"] == "ai_residue"

    def test_meta_missing_uses_default_threshold(self):
        items = self._make_items_with_ai_residue(2)
        assert propose_rules_from_verifier(items, meta={}) == []

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


class TestApplyProposedRule:
    """Test writing proposed rules to lessons.json (origin=verifier、v4.36 前為 generation-rules.json)."""

    def test_apply_success(self, patch_paths):
        rule = {"pattern": "test pattern", "rule": "test rule", "source": "test"}
        ok, msg = apply_proposed_rule(rule)
        assert ok is True
        assert "已寫入" in msg

        data = load_generation_rules()
        patterns = [r["pattern"] for r in data["avoid_patterns"]]
        assert "test pattern" in patterns

    def test_apply_dedup(self, patch_paths):
        rule = {"pattern": "dup pattern", "rule": "test", "source": "test"}
        ok1, _ = apply_proposed_rule(rule)
        assert ok1 is True
        ok2, msg = apply_proposed_rule(rule)
        assert ok2 is False
        assert "已存在" in msg

    def test_apply_appends(self, patch_paths):
        ok1, _ = apply_proposed_rule({"pattern": "first", "rule": "r1", "source": "s1"})
        ok2, _ = apply_proposed_rule(
            {"pattern": "second", "rule": "r2", "source": "s2"}
        )
        assert ok1 and ok2
        data = load_generation_rules()
        patterns = [r["pattern"] for r in data["avoid_patterns"]]
        assert "first" in patterns
        assert "second" in patterns


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
