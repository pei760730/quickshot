import json
from pathlib import Path


def test_valid_skills_contains_vnext_and_active_and_count_7():
    """engine v5.43 (Phase 5 真退役) 後、valid_skills 從 19 縮為 7。

    保留：5 vNext core + harden（active /harden command）+ skill-creator（MCP 內建）
    退役：12 個合併 / 降級 / 升級為主體的 skill
    """
    registry_path = Path(__file__).resolve().parent.parent / "scripts" / "lint" / "canonical-registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    valid_skills = payload.get("valid_skills", [])

    vnext = {"orientation", "discovery", "generation", "quality", "distillation"}
    active_legacy = {"harden", "skill-creator"}
    retired = {
        "flow-operator", "title-generator", "humanizer", "hook-killer",
        "script-verifier", "flow-maximizer", "series-engine", "viral-knowledge",
        "interview-navigator", "topic-architect", "topic-researcher", "trend-adapter",
    }

    assert vnext.issubset(valid_skills)
    assert active_legacy.issubset(valid_skills)
    assert retired.isdisjoint(valid_skills), "退役 skill 不該再出現在 valid_skills"
    assert len(valid_skills) == 7
