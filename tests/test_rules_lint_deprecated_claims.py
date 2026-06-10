"""Regression tests for deprecated stale-claim detection (canonical-registry v2.7).

背景：2026-06 第三輪審視發現 territory-lint 重新引入後、多份文件仍殘留
「territory-lint 已退役」舊敘述（doc-vs-reality 矛盾）。registry 加 claims 類
deprecated_states 條目、rules-lint 掃描範圍內（CLAUDE.md / README / AGENTS /
.claude/rules+commands）擋同類敘述回歸。
"""

import json
from pathlib import Path

from path_bootstrap import load_rules_lint_module

REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "lint" / "canonical-registry.json"
)


def _load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_registry_has_stale_claim_entries():
    registry = _load_registry()
    claims = registry.get("deprecated_states", {}).get("claims", {})
    assert "territory-lint 已退役" in claims
    assert "單 Claude agent 不適用" in claims


def test_stale_claim_flagged_as_error(tmp_path):
    rules_lint = load_rules_lint_module()
    registry = _load_registry()
    content = "本 template 的 territory-lint 已退役、不用理它。\n"
    errors = []
    rules_lint.check_deprecated_states(
        content, tmp_path / "workflow.md", registry, errors
    )
    hits = [e for e in errors if e.get("check") == "deprecated_state"]
    assert len(hits) == 1
    assert "territory-lint 已退役" in hits[0]["message"]


def test_stale_claim_skipped_in_deprecation_notice_context(tmp_path):
    rules_lint = load_rules_lint_module()
    registry = _load_registry()
    # 行內含 skip pattern（「移除」）→ 屬解釋性脈絡、不報錯
    content = "registry 已移除舊條目、勿再寫 territory-lint 已退役 這類敘述。\n"
    errors = []
    rules_lint.check_deprecated_states(
        content, tmp_path / "workflow.md", registry, errors
    )
    hits = [e for e in errors if e.get("check") == "deprecated_state"]
    assert hits == []
