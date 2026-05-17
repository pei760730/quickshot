from path_bootstrap import bootstrap_engine_test_sys_path

bootstrap_engine_test_sys_path()

import client_pollution_scanner as s  # noqa: E402


def test_load_forbidden_terms_reads_marker_block(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    p.write_text(
        "\n".join(
            [
                "x",
                s.POLLUTION_MARKER_START,
                "- term-a",
                "- term-b",
                s.POLLUTION_MARKER_END,
            ]
        ),
        encoding="utf-8",
    )
    assert s.load_forbidden_terms(p) == ["term-a", "term-b"]


def test_load_forbidden_terms_missing_marker_or_file_returns_empty(tmp_path):
    assert s.load_forbidden_terms(tmp_path / "missing.md") == []

    p = tmp_path / "CLAUDE.local.md"
    p.write_text("- no marker", encoding="utf-8")
    assert s.load_forbidden_terms(p) == []


def test_scan_pollution_skips_excluded_and_placeholder(tmp_path):
    (tmp_path / "01-data-brain").mkdir(parents=True)
    (tmp_path / "00-control-center").mkdir(parents=True)

    good = tmp_path / "01-data-brain" / "a.md"
    excluded = tmp_path / "01-data-brain" / "index.md"
    placeholder = tmp_path / "00-control-center" / "template.md"

    good.write_text("contains term-a", encoding="utf-8")
    excluded.write_text("contains term-a", encoding="utf-8")
    placeholder.write_text("{{BRAND_NAME}} term-a", encoding="utf-8")

    hits = s.scan_pollution(tmp_path, ["term-a"])
    assert hits == [("01-data-brain/a.md", "term-a")]


def test_scan_pollution_empty_terms_short_circuits(tmp_path):
    assert s.scan_pollution(tmp_path, []) == []
