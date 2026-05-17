from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parent.parent / "scripts" / "lint" / "brand_ref_lint.py"
    spec = spec_from_file_location("brand_ref_lint", script)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "01-data-brain").mkdir(parents=True)
    (tmp_path / "01-data-brain" / "brand.md").write_text(
        "## [0] A\n\n## [3] B\n\n## [8] C\n",
        encoding="utf-8",
    )
    (tmp_path / "02-skill-factory" / "generation").mkdir(parents=True)
    (tmp_path / "02-skill-factory" / "shared-references").mkdir(parents=True)
    return tmp_path


def test_error_for_missing_brand_section(tmp_path):
    module = _load_module()
    root = _make_repo(tmp_path)
    (root / "02-skill-factory" / "generation" / "SKILL.md").write_text(
        "# S\n引用 brand.md [13]\n",
        encoding="utf-8",
    )

    issues, _manifest = module.run_lint(root)
    assert any(i["check"] == "brand_ref_missing_section" and i["severity"] == "ERROR" for i in issues)


def test_warn_for_declaration_and_inline_mismatch(tmp_path):
    module = _load_module()
    root = _make_repo(tmp_path)
    (root / "02-skill-factory" / "generation" / "SKILL.md").write_text(
        """---
brand-refs: [3, 6]
---

text brand.md [3]
text brand.md [8]
""",
        encoding="utf-8",
    )

    issues, _manifest = module.run_lint(root)
    checks = {i["check"] for i in issues if i["severity"] == "WARN"}
    assert "brand_ref_declaration_missing" in checks
    assert "brand_ref_overdeclared" in checks


def test_manifest_plain_and_json_output(tmp_path, capsys):
    module = _load_module()
    root = _make_repo(tmp_path)
    (root / "02-skill-factory" / "generation" / "SKILL.md").write_text(
        "brand.md [0]\nbrand.md [3]\n",
        encoding="utf-8",
    )

    _issues, manifest = module.run_lint(root)
    module._print_manifest(manifest, json_mode=False)
    plain = capsys.readouterr().out
    assert "02-skill-factory/generation/SKILL.md: [0, 3]" in plain

    module._print_manifest(manifest, json_mode=True)
    json_out = capsys.readouterr().out
    assert '"02-skill-factory/generation/SKILL.md": [' in json_out
    assert "0" in json_out and "3" in json_out
