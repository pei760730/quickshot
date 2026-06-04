"""Cross-platform portability guards.

CI runs Linux-only, where POSIX modules like ``fcntl`` always import — so a
regression to an unconditional ``import fcntl`` passes CI yet breaks the CLI
on a Windows operator's machine (where ``video-ops.py`` is the SSoT entry for
every state write). These tests encode that lesson as a guard so the failure
mode that hid behind Linux-only CI can't return silently.
"""

import ast
import builtins
import importlib
import sys
from pathlib import Path

import pytest
from path_bootstrap import bootstrap_test_sys_path

_PROJECT_ROOT_RAW, _OPS_LIB_ROOT = bootstrap_test_sys_path()
PROJECT_ROOT = Path(_PROJECT_ROOT_RAW)

# Modules that exist only on POSIX. An unconditional top-level import of any of
# these makes the importing module fail to load on Windows.
POSIX_ONLY = {"fcntl", "termios", "grp", "pwd", "posix", "resource", "syslog"}


def _guard_scan_files() -> list[Path]:
    files = []
    for sub in ("scripts", "tests"):
        files.extend((PROJECT_ROOT / sub).rglob("*.py"))
    return sorted(files)


def _toplevel_imports(tree: ast.Module) -> set[str]:
    """Module-level import names (NOT those guarded inside try/except, which
    live under an ``ast.Try`` node rather than directly in the module body)."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_no_unconditional_posix_imports():
    """No script may import a POSIX-only module at module top level unguarded.

    Guarded imports (inside ``try: import fcntl / except ImportError``) are
    fine — they live under an ast.Try node, not the module body, so they are
    not flagged here.
    """
    offenders: list[str] = []
    for py in sorted((PROJECT_ROOT / "scripts").rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - surfaced by compileall instead
            continue
        bad = _toplevel_imports(tree) & POSIX_ONLY
        if bad:
            offenders.append(f"{py.relative_to(PROJECT_ROOT).as_posix()}: {sorted(bad)}")
    assert not offenders, (
        "POSIX-only modules imported unconditionally (breaks on Windows; "
        "wrap in try/except ImportError with a fallback): " + "; ".join(offenders)
    )


def test_storage_imports_and_saves_without_fcntl(tmp_path, monkeypatch):
    """storage.py must import and save even when fcntl is unavailable.

    Simulates Windows by hiding fcntl during (re)import; the module should fall
    back to msvcrt or a no-op lock while atomic tempfile+replace still writes
    the file correctly.
    """
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fcntl":
            raise ImportError("simulated: no fcntl on Windows")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    for mod in ("fcntl", "lib.storage", "scripts.ops.lib.storage"):
        sys.modules.pop(mod, None)

    storage = importlib.import_module("lib.storage")

    target = tmp_path / "sample.json"
    payload = {"_meta": {"v": 1}, "items": ["中文", "emoji ✓"]}
    storage.save_json(target, payload, update_meta=False)

    assert target.exists()
    reloaded = storage.load_json(target, {}, label="sample")
    assert reloaded == payload
    # No leftover temp shards from the atomic write.
    assert not list(tmp_path.glob(".sample_*.tmp"))


def _is_entry_point(text: str) -> bool:
    return '__name__ == "__main__"' in text or "__name__ == '__main__'" in text


def _forces_utf8(text: str) -> bool:
    return (
        'reconfigure(encoding="utf-8")' in text
        or "reconfigure(encoding='utf-8')" in text
    )


def _has_cp950_unsafe_chars(text: str) -> bool:
    """True if text contains a char the Windows cp950 console codec can't encode
    (e.g. emoji ✓ ❌ 📊 ⚠️). The cp950 codec ships with CPython on every OS, so
    this check is identical on Linux CI and Windows."""
    try:
        text.encode("cp950")
        return False
    except UnicodeEncodeError:
        return True


def _attribute_chain(node: ast.AST) -> str | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _keyword_is_true(call: ast.Call, name: str) -> bool:
    return any(
        keyword.arg == name
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in call.keywords
    )


def test_text_subprocess_calls_force_utf8():
    """Text-mode subprocess calls must pin UTF-8 decoding.

    Without an explicit encoding, ``subprocess`` uses the process locale for
    stdout/stderr decoding. On Windows cp950 that can crash with
    UnicodeDecodeError when git emits UTF-8 paths or messages.
    """
    text_subprocess_calls = {
        "subprocess.run",
        "subprocess.check_output",
        "subprocess.Popen",
        "subprocess.check_call",
    }
    offenders: list[str] = []
    for py in _guard_scan_files():
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - surfaced by compileall instead
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _attribute_chain(node.func) not in text_subprocess_calls:
                continue
            if not (
                _keyword_is_true(node, "text")
                or _keyword_is_true(node, "universal_newlines")
            ):
                continue
            if any(keyword.arg == "encoding" for keyword in node.keywords):
                continue
            offenders.append(f"{py.relative_to(PROJECT_ROOT).as_posix()}:{node.lineno}")
    assert not offenders, (
        "text-mode subprocess 必帶 encoding='utf-8'（避免 Windows cp950 解碼崩潰）: "
        + "; ".join(offenders)
    )

def test_emoji_entry_points_force_utf8():
    """Any CLI entry point that prints emoji must force UTF-8 stdout/stderr.

    Without it, piped / redirected / captured output crashes with
    UnicodeEncodeError on a non-UTF-8 locale (Windows cp950) — the H2 failure
    mode. CI is Linux-only so this guard is what keeps Windows from regressing.
    """
    offenders: list[str] = []
    for py in _guard_scan_files():
        text = py.read_text(encoding="utf-8")
        if not _is_entry_point(text):
            continue
        if _has_cp950_unsafe_chars(text) and not _forces_utf8(text):
            offenders.append(py.relative_to(PROJECT_ROOT).as_posix())
    assert not offenders, (
        "entry points emit emoji but don't force UTF-8 stdout (will crash when "
        "piped on Windows cp950); add the reconfigure(encoding='utf-8') block to "
        "main(): " + "; ".join(offenders)
    )


@pytest.mark.parametrize("mod_name", ["lib.storage", "scripts.ops.lib.storage"])
def test_storage_lock_helpers_exist(mod_name):
    """Both import aliases expose the portable lock shim."""
    sys.modules.pop(mod_name, None)
    mod = importlib.import_module(mod_name)
    assert callable(mod._acquire_lock)
    assert callable(mod._release_lock)
