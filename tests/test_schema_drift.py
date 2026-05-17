from lib import schema_drift


def test_schema_drift_detects_required_rename_as_breaking(monkeypatch):
    old = "| `origin` | string | 必填 |\n"
    new = "| `source` | string | 必填 |\n"

    def fake_show(ref, rel):
        return old

    monkeypatch.setattr(schema_drift, "_git_show", fake_show)
    monkeypatch.setattr(schema_drift.Path, "glob", lambda self, pat: [schema_drift.ROOT / "docs" / "contracts" / "lessons-schema.md"])
    monkeypatch.setattr(schema_drift.Path, "read_text", lambda self, encoding="utf-8": new)

    drifts = schema_drift._collect_md_drifts(base_ref="x", head_ref="y")
    assert any(d["level"] == "breaking" for d in drifts)
