from path_bootstrap import bootstrap_engine_test_sys_path

bootstrap_engine_test_sys_path()

import schema_migration_detector as d  # noqa: E402


def test_is_schema_related_path_matches_prefix_and_suffix():
    assert d.is_schema_related_path("docs/contracts/lessons-schema.md") is True
    assert d.is_schema_related_path("data/template/lessons.json") is True
    assert d.is_schema_related_path("foo/bar/schema.json") is True
    assert d.is_schema_related_path("scripts/engine/bump_engine.py") is False


def test_detect_schema_migration_true_when_any_schema_file():
    assert d.detect_schema_migration(["a.md", "docs/contracts/todos-schema.md"]) is True
    assert d.detect_schema_migration(["a.md", "b.py"]) is False


def test_detect_schema_migration_in_repo_filters_nonexistent(tmp_path):
    (tmp_path / "docs/contracts").mkdir(parents=True)
    (tmp_path / "docs/contracts/lessons-schema.md").write_text("x", encoding="utf-8")

    hits = d.detect_schema_migration_in_repo(
        tmp_path,
        [
            "docs/contracts/lessons-schema.md",
            "docs/contracts/missing-schema.md",
            "scripts/engine/x.py",
        ],
    )
    assert hits == ["docs/contracts/lessons-schema.md"]


def test_detect_schema_migration_marker_returns_trimmed_hits():
    text = "\n".join(
        [
            "normal line",
            "  🚨 schema-migration: run migrate_lessons_v2  ",
            "🚨 Schema Migration required before sync",
            "other",
        ]
    )

    hits = d.detect_schema_migration_marker(text)
    assert hits == [
        "🚨 schema-migration: run migrate_lessons_v2",
        "🚨 Schema Migration required before sync",
    ]


def test_detect_schema_migration_marker_handles_no_hits():
    assert d.detect_schema_migration_marker("all good\nnothing here") == []
    assert d.has_schema_migration_marker("all good\nnothing here") is False


def test_has_schema_migration_marker_true_when_hit_exists():
    assert d.has_schema_migration_marker("prefix\n🚨 schema migration now\nsuffix") is True


def test_detect_schema_migration_marker_ignores_inline_mentions():
    text = "note: 🚨 schema-migration should not trigger as marker"
    assert d.detect_schema_migration_marker(text) == []
    assert d.has_schema_migration_marker(text) is False
