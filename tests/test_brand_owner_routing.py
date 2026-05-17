import json
from datetime import date
from pathlib import Path

from conftest import write_sharded_pipeline
from scripts.utils.lib.adoption_gate import _get_section_owners, collect_items


def test_brand_owner_lookup_default_operator(operator_fixture):
    owners = _get_section_owners(operator_fixture)
    assert owners["1"] == "auto"
    assert owners["2"] == "auto"
    assert owners["3"] == "auto"
    assert owners["4"] == operator_fixture
    assert owners["6"] == operator_fixture
    assert owners["8"] == operator_fixture


def test_brand_auto_touch_and_kai_routing(
    tmp_path: Path, operator_fixture, patch_operator_registry
):
    (tmp_path / "data" / operator_fixture).mkdir(parents=True)
    (tmp_path / "01-data-brain").mkdir(parents=True)
    write_sharded_pipeline(
        tmp_path / "data" / operator_fixture, {"_meta": {}, "items": []}
    )
    (tmp_path / "data" / operator_fixture / "todos.json").write_text(
        '{"todos": []}', encoding="utf-8"
    )

    brand = """## [1] 能力\n<!-- last_updated: 2026-02-01 -->\n## [4] 洞察\n<!-- last_updated: 2026-02-01 -->\n"""
    brand_path = tmp_path / "01-data-brain" / "brand.md"
    brand_path.write_text(brand, encoding="utf-8")

    items, auto_messages = collect_items(
        tmp_path, today=date(2026, 4, 30), dry_run=False, operator=operator_fixture
    )

    assert any("brand [1]" in msg for msg in auto_messages)
    assert any(i.owner == operator_fixture and "brand [4]" in i.message for i in items)
    assert not any(i.owner == "employee" and "brand [1]" in i.message for i in items)

    updated = brand_path.read_text(encoding="utf-8")
    assert "last_updated: 2026-04-30" in updated

    monitor = json.loads(
        (tmp_path / "data" / operator_fixture / "brand-monitor.json").read_text(
            encoding="utf-8"
        )
    )
    assert any(
        i.get("section") == "1" and i.get("source") == "auto" for i in monitor["items"]
    )
