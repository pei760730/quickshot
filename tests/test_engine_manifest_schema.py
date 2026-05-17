"""Regression tests for engine-manifest contract layering (introduced v5.95)."""

import json
from pathlib import Path


def test_manifest_uses_semantic_and_factual_contract_layers():
    manifest = json.loads(Path("engine-manifest.json").read_text(encoding="utf-8"))

    assert "contract_files" not in manifest
    assert isinstance(manifest.get("semantic_contracts"), dict)
    assert isinstance(manifest.get("factual_contracts"), dict)
    # 引擎 schema 從 v5.95 引入 semantic / factual 分層；後續 bump（5.96+）
    # 不影響此 regression 的本意（schema 結構穩定）、用最低版本檢核取代硬編。
    version = manifest["_meta"]["engine_version"]
    assert tuple(int(x) for x in version.split(".")) >= (5, 95), (
        f"engine_version 不該低於 5.95（schema 分層引入版）、實際 {version}"
    )


def test_contract_layer_examples_are_classified_by_behavior():
    manifest = json.loads(Path("engine-manifest.json").read_text(encoding="utf-8"))
    semantic = manifest["semantic_contracts"]
    factual = manifest["factual_contracts"]

    assert "docs/contracts/sync-protocol.md" in semantic
    assert "CLAUDE.md" in semantic
    assert "README.md" in factual
    assert "07-changelog/CHANGELOG.md" in factual
    assert set(semantic).isdisjoint(factual)
