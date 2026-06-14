"""script_path 越界防護：destructive 檔案操作不可碰 repo 外的檔。"""

from lib.pipeline import resolve_within_repo


def test_allows_in_repo_path(tmp_path):
    """repo 內的相對路徑 → 回解析後絕對路徑。"""
    got = resolve_within_repo("03-production-line/02-ready-to-shoot/x.md", root=tmp_path)
    assert got is not None
    assert got.is_relative_to(tmp_path.resolve())


def test_blocks_absolute_path(tmp_path):
    """絕對路徑 → None（跨平台：POSIX /etc、Windows 會被導到 C:\\etc）。"""
    assert resolve_within_repo("/etc/passwd", root=tmp_path) is None


def test_blocks_dotdot_traversal(tmp_path):
    """.. 逃出 repo → None。"""
    assert resolve_within_repo("../../outside.txt", root=tmp_path) is None
    assert resolve_within_repo("a/b/../../../../escape", root=tmp_path) is None


def test_empty_or_none_safe(tmp_path):
    """空字串解析為 root 自身（在 repo 內、合法）；不炸。"""
    assert resolve_within_repo("", root=tmp_path) is not None
