from path_bootstrap import load_module_from_repo


def _module():
    return load_module_from_repo("scripts/utils/sync-engine.py", "sync_engine")


def test_detect_engine_client_mode():
    m = _module()
    manifest = {"_meta": {"client": {"name": "kai", "repo_type": "engine+client"}}}
    assert m.detect_sync_mode(manifest) == "engine+client"
    assert m.should_skip_client_layers(manifest) is True


def test_detect_pure_engine_mode():
    m = _module()
    manifest = {"_meta": {"engine_version": "4.51"}}
    assert m.detect_sync_mode(manifest) == "pure-engine"
    assert m.should_skip_client_layers(manifest) is False


def test_contract_layers_are_both_sync_candidates():
    m = _module()
    manifest = {
        "semantic_contracts": {"docs/contracts/sync-protocol.md": "2.2"},
        "factual_contracts": {"README.md": "8.9"},
    }
    layers = m.get_sync_contract_layers(manifest)
    assert layers["semantic_contracts"] == {"docs/contracts/sync-protocol.md": "2.2"}
    assert layers["factual_contracts"] == {"README.md": "8.9"}
    assert m.classify_sync_path(manifest, "docs/contracts/sync-protocol.md") == "semantic"
    assert m.classify_sync_path(manifest, "README.md") == "factual"


def test_sync_notices_distinguish_semantic_and_factual():
    m = _module()
    manifest = {
        "semantic_contracts": {"docs/contracts/sync-protocol.md": "2.2"},
        "factual_contracts": {"README.md": "8.9"},
    }
    assert "規則變動" in m.sync_notice_for_path(manifest, "docs/contracts/sync-protocol.md")
    assert "事實對齊" in m.sync_notice_for_path(manifest, "README.md")
