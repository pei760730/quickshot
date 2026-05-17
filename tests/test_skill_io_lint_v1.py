from path_bootstrap import load_module_from_repo


def test_parse_contract_v1_replaces_default(tmp_path, monkeypatch):
    schema = tmp_path / "schema.md"
    schema.write_text(
        """
| field | type | required |
| --- | --- | --- |
| vid | string | yes |
| skill | string | yes |
| input_hash | string | yes |

| generation | 核心腳本, 毒舌總結 |
""".strip(),
        encoding="utf-8",
    )
    mod = load_module_from_repo("scripts/lint/skill-io-lint.py", "skill_io_lint")
    monkeypatch.setattr(mod, "CONTRACT", schema)
    spec = mod._parse_contract()
    assert "input_hash" in spec["frontmatter_required"]
    assert spec != mod.DEFAULT_SPEC


def test_strict_mode_missing_required_section_is_error(tmp_path, monkeypatch):
    schema = tmp_path / "schema.md"
    schema.write_text(
        """
| field | type | required |
| --- | --- | --- |
| vid | string | yes |
| skill | string | yes |
| skill_version | string | yes |
| generated_at | string | yes |

| generation | 核心腳本 |
""".strip(),
        encoding="utf-8",
    )
    script_dir = tmp_path / "03-production-line"
    script_dir.mkdir(parents=True)
    (script_dir / "x.md").write_text(
        "---\nvid: VID-001\nskill: generation\nskill_version: 1.40\ngenerated_at: 2026-01-01\n---\n\n## 其他段落\n",
        encoding="utf-8",
    )
    mod = load_module_from_repo("scripts/lint/skill-io-lint.py", "skill_io_lint")
    monkeypatch.setattr(mod, "CONTRACT", schema)
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    issues = mod.run_lint()
    assert issues
    assert all(x["severity"] == "ERROR" for x in issues)
