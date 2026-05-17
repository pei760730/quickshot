#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync-engine helper（step 8：判斷 client repo vs pure engine repo）"""

from __future__ import annotations

import json
from pathlib import Path


SEMANTIC_SYNC_MESSAGE = "⚠️ 規則變動：semantic_contracts 更新，會影響客戶 Claude 行為；請先讀 CHANGELOG / migration。"
FACTUAL_SYNC_MESSAGE = "ℹ️ 事實對齊：factual_contracts 更新，只是文件/歷史/版本描述同步，可視情況套用。"


def load_manifest(path: Path | str = "engine-manifest.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def has_client_meta(manifest: dict) -> bool:
    client = manifest.get("_meta", {}).get("client")
    if not isinstance(client, dict):
        return False
    return bool(client.get("name") and client.get("repo_type"))


def detect_sync_mode(manifest: dict) -> str:
    """有 _meta.client → engine+client；否則 pure-engine。"""
    return "engine+client" if has_client_meta(manifest) else "pure-engine"


def should_skip_client_layers(manifest: dict) -> bool:
    """step 8: client repo 不覆蓋 data/content 層。"""
    return detect_sync_mode(manifest) == "engine+client"


def get_sync_contract_layers(manifest: dict) -> dict[str, dict]:
    """Return manifest contract layers that should be considered for sync.

    Both layers are sync candidates. The layer name controls UX severity:
    semantic_contracts are rule/API changes; factual_contracts are optional
    fact-alignment updates. Legacy manifests expose contract_files as semantic.
    """
    semantic = manifest.get("semantic_contracts")
    factual = manifest.get("factual_contracts")
    if isinstance(semantic, dict) or isinstance(factual, dict):
        return {
            "semantic_contracts": semantic if isinstance(semantic, dict) else {},
            "factual_contracts": factual if isinstance(factual, dict) else {},
        }

    legacy = manifest.get("contract_files")
    if isinstance(legacy, dict):
        return {"semantic_contracts": legacy, "factual_contracts": {}}
    return {"semantic_contracts": {}, "factual_contracts": {}}


def classify_sync_path(manifest: dict, path: str) -> str | None:
    """Return semantic/factual classification for a manifest-tracked path."""
    layers = get_sync_contract_layers(manifest)
    if path in layers["semantic_contracts"]:
        return "semantic"
    if path in layers["factual_contracts"]:
        return "factual"
    return None


def sync_notice_for_path(manifest: dict, path: str) -> str | None:
    """Return customer-facing sync notice for a changed path, if classified."""
    layer = classify_sync_path(manifest, path)
    if layer == "semantic":
        return SEMANTIC_SYNC_MESSAGE
    if layer == "factual":
        return FACTUAL_SYNC_MESSAGE
    return None


if __name__ == "__main__":
    m = load_manifest()
    mode = detect_sync_mode(m)
    print(mode)
