#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用原子性 JSON 讀寫。
取代原本 save_tracking / save_ideas / save_performance_patterns 三份重複程式碼。
"""

import json
import tempfile
from pathlib import Path

from .config import today_str

# 跨平台檔案鎖：POSIX 用 fcntl.flock、Windows 用 msvcrt.locking、
# 兩者皆無時退化為 no-op。退化不影響資料安全 —— save_json 的不寫壞檔保證
# 來自 tempfile + atomic replace；此鎖僅多一層防並行寫衝突。
try:
    import fcntl

    def _acquire_lock(lock_fileobj):
        fcntl.flock(lock_fileobj.fileno(), fcntl.LOCK_EX)

    def _release_lock(lock_fileobj):
        fcntl.flock(lock_fileobj.fileno(), fcntl.LOCK_UN)

except ImportError:  # Windows 無 fcntl
    try:
        import msvcrt

        def _acquire_lock(lock_fileobj):
            lock_fileobj.seek(0)
            msvcrt.locking(lock_fileobj.fileno(), msvcrt.LK_LOCK, 1)

        def _release_lock(lock_fileobj):
            lock_fileobj.seek(0)
            msvcrt.locking(lock_fileobj.fileno(), msvcrt.LK_UNLCK, 1)

    except ImportError:  # 平台既無 fcntl 也無 msvcrt：退化為 no-op
        def _acquire_lock(lock_fileobj):
            pass

        def _release_lock(lock_fileobj):
            pass

def _lock_path(filepath):
    """取得對應的鎖檔路徑（與檔案同目錄）"""
    p = Path(filepath)
    return p.parent / f".{p.stem}.lock"


def load_json(filepath, empty_struct, label=""):
    """讀取 JSON 檔案，不存在回傳 empty_struct，格式損壞則報錯退出。"""
    p = Path(filepath)
    if not p.exists():
        print(f"⚠️ {p} 不存在，回傳空結構")
        return empty_struct
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ {label or p.name} 格式損壞（{e}），請檢查或從 git 還原")
        raise SystemExit(1)
    except PermissionError:
        print(f"❌ 無權限讀取 {p}")
        raise SystemExit(1)


def save_json(filepath, data, update_meta=True):
    """原子性寫入 JSON（檔案鎖 + tempfile + rename，防並行衝突與 crash 損壞）。"""
    p = Path(filepath)
    lock_file = _lock_path(filepath)
    if update_meta and "_meta" in data:
        data["_meta"]["last_updated"] = today_str()

    lock_file.parent.mkdir(parents=True, exist_ok=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "w") as lf:
        _acquire_lock(lf)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(p.parent), prefix=f".{p.stem}_", suffix=".tmp"
            )
            try:
                with open(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                Path(tmp_path).replace(p)
            except Exception:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass
                raise
        finally:
            _release_lock(lf)
