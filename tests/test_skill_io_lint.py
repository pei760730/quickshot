from pathlib import Path

from path_bootstrap import load_module_from_repo


def test_skill_io_lint_detects_missing_frontmatter(tmp_path, monkeypatch):
    root = tmp_path
    (root / "docs" / "contracts").mkdir(parents=True)
    (root / "docs" / "contracts" / "skill-io-schema.md").write_text("", encoding="utf-8")
    prod = root / "03-production-line"
    prod.mkdir(parents=True)
    (prod / "sample.md").write_text("---\nskill: generation\n---\n## 核心腳本\nabc", encoding="utf-8")

    module = load_module_from_repo("scripts/lint/skill-io-lint.py", "skill_io_lint")

    monkeypatch.setattr(module, "REPO_ROOT", root)
    monkeypatch.setattr(module, "CONTRACT", root / "docs" / "contracts" / "skill-io-schema.md")
    issues = module.run_lint()
    assert any(i["check"] == "skill_io_frontmatter" for i in issues)


def _load_module():
    return load_module_from_repo("scripts/lint/skill-io-lint.py", "skill_io_lint")


def _write_contract(path: Path):
    path.write_text(
        """
```yaml
validation_rules:
  - id: output_contract_section_present
    level: ERROR
    check: "generation"
  - id: quality_output_contract_present
    level: ERROR
    check: "quality"
```
""".strip(),
        encoding="utf-8",
    )


def _write_generation_skill(skills_root: Path):
    p = skills_root / "generation" / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# X\n\n## Output Contract\nUse --skill generation and --mode dual-track.\n\n## Next\n",
        encoding="utf-8",
    )


def _write_quality_skill(skills_root: Path):
    p = skills_root / "quality" / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# X\n\nphase=check\n\n## Output Contract\nUse record-verifier-scores.\n\n## Next\n",
        encoding="utf-8",
    )


class TestOutputContractPresent:
    def test_generation_skill_pass(self, tmp_path, monkeypatch):
        module = _load_module()
        root = tmp_path
        (root / "docs" / "contracts").mkdir(parents=True)
        _write_contract(root / "docs" / "contracts" / "skill-io-schema.md")
        _write_generation_skill(root / "02-skill-factory")
        _write_quality_skill(root / "02-skill-factory")
        (root / "03-production-line").mkdir(parents=True)

        monkeypatch.setattr(module, "REPO_ROOT", root)
        monkeypatch.setattr(module, "CONTRACT", root / "docs" / "contracts" / "skill-io-schema.md")
        issues = module.run_lint()
        assert not [i for i in issues if i["check"] == "output_contract_section_present"]

    def test_generation_heading_missing_fails(self, tmp_path, monkeypatch):
        module = _load_module()
        root = tmp_path
        (root / "docs" / "contracts").mkdir(parents=True)
        _write_contract(root / "docs" / "contracts" / "skill-io-schema.md")
        _write_generation_skill(root / "02-skill-factory")
        _write_quality_skill(root / "02-skill-factory")
        broken = root / "02-skill-factory" / "generation" / "SKILL.md"
        broken.write_text(
            "# X\n\n## §Output Contract\nUse --skill generation and --mode dual-track.\n\n## Next\n",
            encoding="utf-8",
        )
        (root / "03-production-line").mkdir(parents=True)

        monkeypatch.setattr(module, "REPO_ROOT", root)
        monkeypatch.setattr(module, "CONTRACT", root / "docs" / "contracts" / "skill-io-schema.md")
        issues = module.run_lint()
        assert any(i["check"] == "output_contract_section_present" for i in issues)

    def test_generation_mode_string_missing_fails(self, tmp_path, monkeypatch):
        module = _load_module()
        root = tmp_path
        (root / "docs" / "contracts").mkdir(parents=True)
        _write_contract(root / "docs" / "contracts" / "skill-io-schema.md")
        _write_generation_skill(root / "02-skill-factory")
        _write_quality_skill(root / "02-skill-factory")
        broken = root / "02-skill-factory" / "generation" / "SKILL.md"
        broken.write_text(
            "# X\n\n## Output Contract\nNo skill/mode contract here.\n\n## Next\n",
            encoding="utf-8",
        )
        (root / "03-production-line").mkdir(parents=True)

        monkeypatch.setattr(module, "REPO_ROOT", root)
        monkeypatch.setattr(module, "CONTRACT", root / "docs" / "contracts" / "skill-io-schema.md")
        issues = module.run_lint()
        assert any(i["check"] == "output_contract_section_present" for i in issues)


class TestQualityOutputContractPresent:
    def test_quality_contract_pass(self, tmp_path, monkeypatch):
        module = _load_module()
        root = tmp_path
        (root / "docs" / "contracts").mkdir(parents=True)
        _write_contract(root / "docs" / "contracts" / "skill-io-schema.md")
        _write_generation_skill(root / "02-skill-factory")
        _write_quality_skill(root / "02-skill-factory")
        (root / "03-production-line").mkdir(parents=True)

        monkeypatch.setattr(module, "REPO_ROOT", root)
        monkeypatch.setattr(module, "CONTRACT", root / "docs" / "contracts" / "skill-io-schema.md")
        issues = module.run_lint()
        assert not [i for i in issues if i["check"] == "quality_output_contract_present"]

    def test_quality_string_missing_fails(self, tmp_path, monkeypatch):
        module = _load_module()
        root = tmp_path
        (root / "docs" / "contracts").mkdir(parents=True)
        _write_contract(root / "docs" / "contracts" / "skill-io-schema.md")
        _write_generation_skill(root / "02-skill-factory")
        _write_quality_skill(root / "02-skill-factory")
        broken = root / "02-skill-factory" / "quality" / "SKILL.md"
        broken.write_text(
            "# X\n\n## Output Contract\nVerifier command not mentioned.\n\n## Next\n",
            encoding="utf-8",
        )
        (root / "03-production-line").mkdir(parents=True)

        monkeypatch.setattr(module, "REPO_ROOT", root)
        monkeypatch.setattr(module, "CONTRACT", root / "docs" / "contracts" / "skill-io-schema.md")
        issues = module.run_lint()
        assert any(i["check"] == "quality_output_contract_present" for i in issues)
