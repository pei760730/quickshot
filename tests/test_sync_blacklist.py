"""Tests for sync_blacklist opt-out model (v4.24 refactor).

Design: Main repo = engine + Kai instance. To avoid polluting client repos
with Kai-specific configs (Vercel dashboard, Claude design collaboration etc),
we use a path-based blacklist. Default: every path is engine; exception: paths
matching blacklist (with optional `!negation`) are NOT engine-scoped.
"""
import importlib.util
import json
from pathlib import Path


_utils_cache = {}


def _load_utils():
    """Cache-based loader：dataclass InitVar 處理會因 module 反覆 reload 失敗，只載入一次。"""
    if "u" not in _utils_cache:
        import sys
        repo_root = Path(__file__).resolve().parent.parent
        mod_path = repo_root / "scripts" / "engine" / "engine_version_utils.py"
        spec = importlib.util.spec_from_file_location("engine_version_utils_sync_bl", mod_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[spec.name] = mod  # 讓 dataclass 找得到自己的 module
        spec.loader.exec_module(mod)
        _utils_cache["u"] = mod
    return _utils_cache["u"]


def test_blacklist_simple_data_path():
    u = _load_utils()
    bl = ["data/**"]
    assert u.is_blacklisted("data/kai/pipeline.json", bl) is True
    assert u.is_blacklisted("data/legacy/pipeline.json", bl) is True


def test_blacklist_negation_rescues_exception():
    u = _load_utils()
    bl = ["data/**", "!data/template/**"]
    # Template 是引擎檔案、要同步
    assert u.is_blacklisted("data/template/pipeline.json", bl) is False
    # 其他 data/ 仍然 blacklist
    assert u.is_blacklisted("data/kai/pipeline.json", bl) is True


def test_blacklist_glob_filename_pattern():
    u = _load_utils()
    bl = ["docs/contracts/*-collaboration.md"]
    assert u.is_blacklisted("docs/contracts/design-collaboration.md", bl) is True
    assert u.is_blacklisted("docs/contracts/agent-collaboration.md", bl) is True
    # sync-protocol.md 不 match（沒 -collaboration suffix）
    assert u.is_blacklisted("docs/contracts/sync-protocol.md", bl) is False


def test_blacklist_brand_files():
    u = _load_utils()
    bl = ["01-data-brain/brand*.md", "01-data-brain/cases.md"]
    assert u.is_blacklisted("01-data-brain/brand.md", bl) is True
    assert u.is_blacklisted("01-data-brain/brand-summary.md", bl) is True
    assert u.is_blacklisted("01-data-brain/brand_legacy.md", bl) is True
    assert u.is_blacklisted("01-data-brain/cases.md", bl) is True
    # index.md 不 match（沒 brand 前綴、不是 cases）
    assert u.is_blacklisted("01-data-brain/index.md", bl) is False


def test_blacklist_dashboard_entire_dir():
    u = _load_utils()
    bl = ["dashboard/**"]
    assert u.is_blacklisted("dashboard/build.py", bl) is True
    assert u.is_blacklisted("dashboard/src/index.html", bl) is True
    assert u.is_blacklisted("dashboard/src/design-snapshots/v1.html", bl) is True
    assert u.is_blacklisted("dashboard/vercel.json", bl) is True


def test_non_blacklist_path_is_engine():
    u = _load_utils()
    bl = ["data/**", "dashboard/**"]
    # 其他任何路徑 = engine（同步）
    assert u.is_blacklisted("02-skill-factory/flow-operator/SKILL.md", bl) is False
    assert u.is_blacklisted("scripts/ops/video-ops.py", bl) is False
    assert u.is_blacklisted(".claude/hooks/session-start.sh", bl) is False
    assert u.is_blacklisted("CLAUDE.md", bl) is False
    assert u.is_blacklisted("docs/contracts/sync-protocol.md", bl) is False


def test_default_blacklist_loads_when_no_arg():
    u = _load_utils()
    # 不傳 blacklist → 從 engine-manifest 載入
    # 用 manifest 真實值驗證 data/** 被擋
    assert u.is_blacklisted("data/kai/pipeline.json") is True
    # 非 blacklist 不擋
    assert u.is_blacklisted("scripts/ops/video-ops.py") is False


def test_load_sync_blacklist_reads_manifest():
    u = _load_utils()
    bl = u.load_sync_blacklist()
    assert isinstance(bl, tuple)
    assert len(bl) >= 5  # 至少 data/** + brand 等幾條
    # 驗證 dashboard/** 在（v4.24 後）
    assert "dashboard/**" in bl


def test_load_sync_blacklist_fallback_on_missing_file(tmp_path):
    u = _load_utils()
    fake = tmp_path / "no-such-manifest.json"
    bl = u.load_sync_blacklist(fake)
    # 回 _DEFAULT_BLACKLIST（不 crash）
    assert isinstance(bl, tuple)
    assert len(bl) > 0
    assert "data/**" in bl


def test_load_sync_blacklist_fallback_on_malformed_json(tmp_path):
    u = _load_utils()
    fake = tmp_path / "bad.json"
    fake.write_text("not valid json{{{", encoding="utf-8")
    bl = u.load_sync_blacklist(fake)
    assert isinstance(bl, tuple)
    assert "data/**" in bl


def test_is_data_only_path_backward_compat():
    """舊 API `is_data_only_path` 仍能呼叫、語意對齊新 is_blacklisted。"""
    u = _load_utils()
    # 舊呼叫者不傳 blacklist，是否仍 return 正確
    assert u.is_data_only_path("data/kai/pipeline.json") is True
    assert u.is_data_only_path("data/template/pipeline.json") is False  # negation rescue
    assert u.is_data_only_path("scripts/ops/video-ops.py") is False


def test_blacklist_in_manifest_includes_kai_specific():
    """確認 v4.24 manifest 的 sync_blacklist 確實包含 Kai 特有路徑。"""
    repo_root = Path(__file__).resolve().parent.parent
    m = json.loads((repo_root / "engine-manifest.json").read_text(encoding="utf-8"))
    bl = m["_meta"]["sync_blacklist"]
    # Kai 特有
    assert "dashboard/**" in bl
    assert "docs/contracts/*-collaboration.md" in bl
    # 客戶專屬資料
    assert "data/**" in bl
    # Negation for template
    assert "!data/template/**" in bl
    # v2.1 修 bug：agent-collaboration.md 是通用憲章、要用 negation 豁免
    assert "!docs/contracts/agent-collaboration.md" in bl


def test_agent_collaboration_not_blacklisted_design_is():
    """v2.1 修 bug 驗收：
    - agent-collaboration.md（通用）不該被 blacklist、要推給客戶
    - design-collaboration.md（Kai 特有）該被 blacklist、不推給客戶
    關鍵：negation pattern 優先於正規 pattern。"""
    u = _load_utils()
    bl = [
        "docs/contracts/*-collaboration.md",
        "!docs/contracts/agent-collaboration.md",
    ]
    # 通用憲章：不擋
    assert u.is_blacklisted("docs/contracts/agent-collaboration.md", bl) is False
    # Kai 特有：擋
    assert u.is_blacklisted("docs/contracts/design-collaboration.md", bl) is True
    # 其他 -collaboration.md 檔（未來可能加）：擋（除非明確加 negation）
    assert u.is_blacklisted("docs/contracts/figma-collaboration.md", bl) is True


def test_default_blacklist_fallback_also_protects_agent_collaboration():
    """_DEFAULT_BLACKLIST（manifest 讀不到時的 fallback）也要有 negation。
    避免 fallback 情境下誤擋通用憲章。"""
    u = _load_utils()
    # 不傳 blacklist → 從 manifest 讀（v4.26+ 有 negation）
    # manifest 不可用的情境不容易模擬、直接 import _DEFAULT_BLACKLIST 驗
    assert "!docs/contracts/agent-collaboration.md" in u._DEFAULT_BLACKLIST


def test_engine_files_registry_excludes_kai_specific():
    """engine-manifest 的 contract_files / internal_files（v4.65+）或 legacy `files`（pre-v4.65）
    不該列任何 Kai 特有檔（dashboard/ 或 design-collaboration）。"""
    repo_root = Path(__file__).resolve().parent.parent
    m = json.loads((repo_root / "engine-manifest.json").read_text(encoding="utf-8"))

    # v5.95+ layered：合併 semantic + factual + internal；pre-v5.95 legacy：contract/files
    files = {}
    if any(k in m for k in ("semantic_contracts", "factual_contracts", "contract_files", "internal_files")):
        files.update(m.get("semantic_contracts") or {})
        files.update(m.get("factual_contracts") or {})
        files.update(m.get("contract_files") or {})
        files.update(m.get("internal_files") or {})
    else:
        files = m.get("files") or {}

    dashboard_keys = [k for k in files if k.startswith("dashboard/")]
    assert not dashboard_keys, f"Dashboard keys leaked into engine-manifest: {dashboard_keys}"

    design_keys = [k for k in files if "design-collaboration" in k]
    assert not design_keys, f"Design collaboration leaked: {design_keys}"
