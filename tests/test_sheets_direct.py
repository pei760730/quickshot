"""Tests for sheets-direct.py CLI — 混合架構讀寫工具。

測試策略：
  - 用 importlib 動態載入 sheets-direct.py
  - 清除 lib.* 模組快取避免與 ops/lib 衝突
  - 直接 patch 模組內的 sheets_read / sheets_write / sheets_get_tab_names
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from path_bootstrap import bootstrap_utils_test_sys_path

# ── 路徑 ─────────────────────────────────────────────
UTILS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "utils"
SHEETS_DIRECT = UTILS_DIR / "sheets-direct.py"


def _load_module():
    """Load sheets-direct module with utils/lib taking precedence.

    Temporarily removes cached lib.* modules that point to ops/lib,
    ensures utils/lib is used, then restores state afterwards.
    """
    # Save and remove any cached lib.* modules (from ops/lib via conftest)
    saved_modules = {}
    to_remove = [k for k in sys.modules if k == "lib" or k.startswith("lib.")]
    for k in to_remove:
        saved_modules[k] = sys.modules.pop(k)

    # Ensure utils dir is first on path via shared bootstrap contract.
    utils_path = bootstrap_utils_test_sys_path()

    try:
        spec = importlib.util.spec_from_file_location(
            "sheets_direct", str(SHEETS_DIRECT),
            submodule_search_locations=[],
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        # Restore path
        while utils_path in sys.path:
            sys.path.remove(utils_path)
        # Remove utils/lib.* from cache
        utils_lib_keys = [k for k in sys.modules
                          if (k == "lib" or k.startswith("lib."))
                          and k not in saved_modules]
        for k in utils_lib_keys:
            del sys.modules[k]
        # Restore ops/lib.* modules
        sys.modules.update(saved_modules)


@pytest.fixture
def mod():
    """Load sheets-direct module fresh for each test."""
    return _load_module()


# ── Tests ────────────────────────────────────────────────


class TestCmdRead:
    def test_read_with_default_range(self, mod, capsys):
        mock_read = MagicMock(return_value=[
            ["VID-001", "測試", "待拍"],
            ["VID-002", "範例", "已上線"],
        ])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_read(["影片追蹤"])
        out = capsys.readouterr().out
        assert "VID-001" in out
        assert "VID-002" in out
        mock_read.assert_called_once_with("t", "影片追蹤", "A1:Z100")

    def test_read_with_custom_range(self, mod, capsys):
        mock_read = MagicMock(return_value=[["hello"]])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_read(["待辦", "A1:D5"])
        mock_read.assert_called_once_with("t", "待辦", "A1:D5")

    def test_read_empty(self, mod, capsys):
        mock_read = MagicMock(return_value=[])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_read(["空分頁"])
        assert "無資料" in capsys.readouterr().out

    def test_read_no_args(self, mod):
        with pytest.raises(SystemExit):
            mod.cmd_read([])


class TestCmdReadCell:
    def test_read_cell_value(self, mod, capsys):
        mock_read = MagicMock(return_value=[["42"]])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_read_cell(["報表", "B3"])
        assert capsys.readouterr().out.strip() == "42"

    def test_read_cell_empty(self, mod, capsys):
        mock_read = MagicMock(return_value=[])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_read_cell(["報表", "Z99"])
        assert "為空" in capsys.readouterr().out

    def test_read_cell_no_args(self, mod):
        with pytest.raises(SystemExit):
            mod.cmd_read_cell(["只有分頁"])


class TestCmdWriteCell:
    def test_write_single_cell(self, mod, capsys):
        mock_write = MagicMock()
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_write", mock_write):
            mod.cmd_write_cell(["影片追蹤", "H3", "✅ 完整"])
        mock_write.assert_called_once_with("t", "影片追蹤", "H3", [["✅ 完整"]])
        assert "✅" in capsys.readouterr().out

    def test_write_cell_no_args(self, mod):
        with pytest.raises(SystemExit):
            mod.cmd_write_cell(["分頁", "A1"])


class TestCmdTabs:
    def test_list_tabs(self, mod, capsys):
        mock_tabs = MagicMock(return_value=["靈感庫", "影片追蹤", "待辦"])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_get_tab_names", mock_tabs):
            mod.cmd_tabs([])
        out = capsys.readouterr().out
        assert "3 個分頁" in out
        assert "靈感庫" in out


class TestCmdEmployee:
    def test_employee_all(self, mod, capsys):
        mock_read = MagicMock(return_value=[
            ["📊 日報看板", "", "", "", "", ""],
            ["今日動態", "", "", "", "", ""],
            ["本週各人", "", "", "", "", ""],
            ["🟢 異常偵測", "", "", "", "", ""],
            ["───", "", "", "", "", ""],
            ["日期", "姓名", "類別", "做了什麼", "花多久", "備註"],
            ["'2026-03-17", "阿明", "剪輯", "完成初稿", "2hr", ""],
            ["'2026-03-16", "小美", "拍攝", "外景", "3hr", ""],
        ])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_employee([])
        out = capsys.readouterr().out
        assert "阿明" in out
        assert "小美" in out

    def test_employee_filter_date(self, mod, capsys):
        mock_read = MagicMock(return_value=[
            ["", "", "", "", "", ""],
            ["", "", "", "", "", ""],
            ["", "", "", "", "", ""],
            ["", "", "", "", "", ""],
            ["", "", "", "", "", ""],
            ["日期", "姓名", "類別", "做了什麼", "花多久", "備註"],
            ["'2026-03-17", "阿明", "剪輯", "完成", "2hr", ""],
            ["'2026-03-16", "小美", "拍攝", "外景", "3hr", ""],
        ])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_employee(["2026-03-17"])
        out = capsys.readouterr().out
        assert "阿明" in out
        assert "小美" not in out

    def test_employee_empty(self, mod, capsys):
        mock_read = MagicMock(return_value=[])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_employee([])
        assert "無資料" in capsys.readouterr().out


class TestCmdLookupVid:
    def test_lookup_found(self, mod, capsys):
        mock_read = MagicMock(return_value=[
            ["🎬 影片追蹤", "", "", "", "", "", "", ""],
            ["影片碼", "主題", "標籤", "狀態", "上片日", "腳本路徑", "表現", "資料狀態"],
            ["VID-001", "測試", "tag", "已上線", "2026-03-10", "path", "🟢", "✅ 完整"],
        ])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_lookup_vid(["VID-001"])
        out = capsys.readouterr().out
        assert "VID-001" in out
        assert "已上線" in out

    def test_lookup_not_found(self, mod, capsys):
        mock_read = MagicMock(return_value=[
            ["", "", "", "", "", "", "", ""],
            ["影片碼", "主題", "標籤", "狀態", "上片日", "腳本路徑", "表現", "資料狀態"],
            ["VID-001", "測試", "tag", "已上線", "", "", "", ""],
        ])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_lookup_vid(["VID-999"])
        assert "找不到" in capsys.readouterr().out

    def test_lookup_case_insensitive(self, mod, capsys):
        mock_read = MagicMock(return_value=[
            ["", "", "", "", "", "", "", ""],
            ["影片碼", "主題", "標籤", "狀態", "上片日", "腳本路徑", "表現", "資料狀態"],
            ["VID-001", "測試", "tag", "待拍", "", "", "⚪", "—"],
        ])
        with patch.object(mod, "_auth", return_value="t"), \
             patch.object(mod, "sheets_read", mock_read):
            mod.cmd_lookup_vid(["vid-001"])
        assert "VID-001" in capsys.readouterr().out

    def test_lookup_no_args(self, mod):
        with pytest.raises(SystemExit):
            mod.cmd_lookup_vid([])


class TestMain:
    def test_unknown_command(self, mod):
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["sheets-direct.py", "foobar"]):
                mod.main()

    def test_no_args_shows_help(self, mod):
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["sheets-direct.py"]):
                mod.main()
