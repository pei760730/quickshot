from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.engine import engine_lag_detector as eld


def test_fetch_engine_main_without_remote_returns_false(tmp_path: Path) -> None:
    assert eld.fetch_engine_main(tmp_path) is False


def test_compare_versions_behind() -> None:
    assert eld.compare_versions("5.98", "5.99") == "behind"


def test_compare_versions_current() -> None:
    assert eld.compare_versions("5.99", "5.99") == "current"


def test_read_local_engine_version_missing_meta_returns_none(tmp_path: Path) -> None:
    (tmp_path / "engine-manifest.json").write_text(json.dumps({}), encoding="utf-8")

    assert eld.read_local_engine_version(tmp_path) is None


def test_count_remote_schema_migrations_counts_between_local_and_remote(
    tmp_path: Path,
    monkeypatch,
) -> None:
    changelog = """# 系統變更紀錄（CHANGELOG）

---

## v5.99（2026-05-15）

🚨 schema-migration: migrate once

---

## v5.98（2026-05-15）

old entry
"""

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=changelog)

    monkeypatch.setattr(eld.subprocess, "run", fake_run)

    assert eld.count_remote_schema_migrations(tmp_path, "5.98", "5.99") == 1


def test_append_engine_lag_item_adds_kai_gate_with_migration_count(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts.utils.lib import adoption_gate

    monkeypatch.setattr(adoption_gate.eld, "fetch_engine_main", lambda repo: True)
    monkeypatch.setattr(adoption_gate.eld, "read_local_engine_version", lambda repo: "5.98")
    monkeypatch.setattr(adoption_gate.eld, "read_remote_engine_version", lambda repo: "5.99")
    monkeypatch.setattr(adoption_gate.eld, "compare_versions", lambda local, remote: "behind")
    monkeypatch.setattr(
        adoption_gate.eld,
        "count_remote_schema_migrations",
        lambda repo, local, remote: 1,
    )
    items: list[adoption_gate.GateItem] = []

    adoption_gate._append_engine_lag_item(tmp_path, items)

    assert items == [
        adoption_gate.GateItem(
            "E0",
            "kai",
            "🔄 engine 落後 v5.98 → v5.99（含 1 個 🚨 schema-migration、需手動）（說「同步」拉）",
            kind="engine-lag",
        )
    ]


def test_render_report_shows_kai_owned_engine_lag_for_client_operator() -> None:
    from scripts.utils.lib.adoption_gate import GateItem, render_report

    report = render_report(
        [GateItem("E0", "kai", "🔄 engine 落後 v5.98 → v5.99", kind="engine-lag")],
        [],
        operator="longbro",
    )

    assert "[E0] 🔄 engine 落後 v5.98 → v5.99" in report
    assert "1 項需決定" in report
