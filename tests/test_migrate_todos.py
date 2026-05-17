"""Tests for markdown -> todos migration."""

from pathlib import Path

from lib.migrate_todos import run_migration
from lib.todos import load_todos


def test_roundtrip_and_legacy_rename(patch_paths):
    root = Path(patch_paths)
    todo_dir = root / "00-control-center" / "todo"
    (todo_dir / "工作待辦.md").write_text(
        "- [ ] 📊 每週整理 📅2026-03-20\n- [x] 🔗 合併 VID ✅2026-03-16\n",
        encoding="utf-8",
    )
    (todo_dir / "雜事待辦.md").write_text("\n<!-- comment -->\n", encoding="utf-8")

    result = run_migration("kai")
    rows = load_todos("kai")

    assert result["migrated"] == 2
    assert len(rows) == 2
    assert (todo_dir / "工作待辦.legacy.md").exists()
    assert (todo_dir / "雜事待辦.legacy.md").exists()


def test_idempotent(patch_paths):
    root = Path(patch_paths)
    todo_dir = root / "00-control-center" / "todo"
    (todo_dir / "工作待辦.md").write_text("- [ ] A 📅2026-03-20\n", encoding="utf-8")
    (todo_dir / "雜事待辦.md").write_text("", encoding="utf-8")

    run_migration("kai")
    first = len(load_todos("kai"))

    # recreate source markdown and run again; should not duplicate
    (todo_dir / "工作待辦.md").write_text("- [ ] A 📅2026-03-20\n", encoding="utf-8")
    run_migration("kai")
    second = len(load_todos("kai"))

    assert first == second


def test_source_tag_applied(patch_paths):
    """v4.40 P2 修正：migration 按來源 md 加 tag（work / misc）、scanners 才能分組。"""
    root = Path(patch_paths)
    todo_dir = root / "00-control-center" / "todo"
    (todo_dir / "工作待辦.md").write_text(
        "- [ ] 工作任務 A 📅2026-03-20\n- [x] 工作任務 B ✅2026-03-16\n",
        encoding="utf-8",
    )
    (todo_dir / "雜事待辦.md").write_text(
        "- [ ] 雜事任務 C 📅2026-03-21\n",
        encoding="utf-8",
    )

    run_migration("kai")
    rows = load_todos("kai")

    by_title = {r["title"]: r for r in rows}
    assert by_title["工作任務 A"]["tags"] == ["work"]
    assert by_title["工作任務 B"]["tags"] == ["work"]
    assert by_title["雜事任務 C"]["tags"] == ["misc"]
