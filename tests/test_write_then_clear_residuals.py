"""Tests for _compute_clear_range (pure fn) + sheets_get_last_row fallback.

Historical bug: _write_then_clear only cleared up to `old_row_count + 5` rows
after new data. If a previous sync wrote more rows (e.g. 70), a later sync
with fewer rows (e.g. 40) would clear A41:K55 but leave A56:K70 stale.

v2 fix: call sheets_get_last_row() to get the real last row on the Sheet,
then clear from (len(rows)+1) through (actual_last + 10).
"""
import importlib.util
from pathlib import Path


def _load(rel_path, module_name):
    repo_root = Path(__file__).resolve().parent.parent
    mod_path = repo_root / rel_path
    spec = importlib.util.spec_from_file_location(module_name, mod_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


# ── Pure function _compute_clear_range（無 I/O 依賴，直接 exec 單檔）─────

def _compute_clear_range(new_rows_count, actual_last_row, old_row_count=0):
    """Inlined copy of sync_tabs._compute_clear_range for isolated test.
    保持與 sync_tabs.py 同步；任一方改動對方需同步（見下方 contract test）。"""
    clear_start = new_rows_count + 1
    fallback_end = max(old_row_count + 5, clear_start + 10)
    clear_end = max(actual_last_row + 10, fallback_end)
    return clear_start, clear_end


def test_covers_stale_residuals_beyond_old_row_count():
    """Regression: new=40, sheet has 70 stale rows, old_row_count=50.
    clear_end 必須超過 70（歷史殘留）→ 預期 80。"""
    start, end = _compute_clear_range(new_rows_count=40, actual_last_row=70, old_row_count=50)
    assert start == 41
    # max(70+10, 50+5, 41+10) = 80
    assert end == 80


def test_no_residuals_but_buffer_still_clears():
    """新資料比殘留多：仍清 buffer 10 行（對空 range sheets_clear 無害）。"""
    start, end = _compute_clear_range(new_rows_count=100, actual_last_row=30, old_row_count=50)
    assert start == 101
    # max(30+10, 50+5, 101+10) = 111
    assert end == 111


def test_fallback_when_actual_last_is_zero():
    """sheets_get_last_row 失敗回 0 時，用 old_row_count fallback。"""
    start, end = _compute_clear_range(new_rows_count=10, actual_last_row=0, old_row_count=40)
    assert start == 11
    # max(0+10, 40+5, 11+10) = 45
    assert end == 45


def test_minimum_buffer_when_all_small():
    """最小情況：new=5, actual=0, old_row_count=0 → 仍有 10 行保險 buffer。"""
    start, end = _compute_clear_range(new_rows_count=5, actual_last_row=0, old_row_count=0)
    assert start == 6
    # max(0+10, 0+5, 6+10) = 16
    assert end == 16


# ── sheets_get_last_row 邏輯（source-level 驗證，避免 relative import）──

def _extract_sheets_get_last_row_source():
    """從 sheets_api.py 取出 sheets_get_last_row 函式 source。"""
    repo_root = Path(__file__).resolve().parent.parent
    src = (repo_root / "scripts" / "utils" / "lib" / "sheets_api.py").read_text(encoding="utf-8")
    import re
    m = re.search(
        r"(def sheets_get_last_row\([^\)]*\):.*?(?=\n\ndef |\nclass |\Z))",
        src, re.DOTALL,
    )
    assert m, "Could not locate sheets_get_last_row in sheets_api.py"
    return m.group(1)


def test_sheets_get_last_row_returns_zero_on_error():
    """API exception → 回 0（不 crash）。"""
    src = _extract_sheets_get_last_row_source()

    def boom(*a, **k):
        raise RuntimeError("404")

    ns = {"sheets_read": boom}
    exec(src, ns)
    assert ns["sheets_get_last_row"]("tok", "tab") == 0


def test_sheets_get_last_row_returns_len_of_values():
    """正常回傳 len(values)，=最後非空 row（1-indexed）。"""
    src = _extract_sheets_get_last_row_source()
    fake_values = [["h"], ["r1"], ["r2"], [""], [""], ["r5"]]

    def fake_read(token, sheet, range_str="A1:Z2000"):
        assert range_str == "A:A"
        return fake_values

    ns = {"sheets_read": fake_read}
    exec(src, ns)
    assert ns["sheets_get_last_row"]("tok", "tab", "A") == 6


# ── Contract test：sync_tabs._compute_clear_range 跟本檔 inlined copy 一致 ──

def test_sync_tabs_compute_clear_range_matches_inlined_copy():
    """防漂移：sync_tabs 若改邏輯、本測試要更新 inlined copy（保證同步）。"""
    import sys, types
    # 準備 stub 讓 sync_tabs import 不爆
    fake_cfg = types.ModuleType("stub_cfg")
    fake_cfg.PROJECT_ROOT = Path("/tmp")
    fake_cfg.TW_TZ = None
    fake_cfg.SH_TODO = "待辦"
    fake_cfg.SH_REPORT = "報表"
    fake_cfg.OPERATOR_SHEETS = {}
    sys.modules.setdefault("stub_utils_pkg", types.ModuleType("stub_utils_pkg"))

    # 直接用 exec 取得 _compute_clear_range 的 source
    repo_root = Path(__file__).resolve().parent.parent
    src = (repo_root / "scripts" / "utils" / "lib" / "sync_tabs.py").read_text(encoding="utf-8")
    # 取出 _compute_clear_range 整個 function 到獨立 namespace
    import re
    m = re.search(
        r"(def _compute_clear_range\([^\)]*\):.*?(?=\n\ndef |\nclass |\Z))",
        src, re.DOTALL,
    )
    assert m, "Could not locate _compute_clear_range in sync_tabs.py"
    ns = {}
    exec(m.group(1), ns)
    real_fn = ns["_compute_clear_range"]

    # 抽測多個 input 確認兩版一致
    for new_rows, actual, old in [
        (40, 70, 50),
        (100, 30, 50),
        (10, 0, 40),
        (5, 0, 0),
        (0, 0, 0),
    ]:
        expected = _compute_clear_range(new_rows, actual, old)
        got = real_fn(new_rows, actual, old)
        assert got == expected, f"Drift detected: {(new_rows, actual, old)} → real {got} vs inlined {expected}"
