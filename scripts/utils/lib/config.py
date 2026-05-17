#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-to-sheets 共用設定：路徑、常數、分頁名稱。
"""

import os
import sys
from datetime import timezone, timedelta

# ── 路徑 ──────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # → scripts/
PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)  # → repo root
CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH", os.path.join(PROJECT_ROOT, "google-credentials.json")
)
SPREADSHEET_ID = "1k8FjzxoykSoKW9JlBUHw0s_tBpeRi7c9YzfOeb1b3ZU"
# ── API ───────────────────────────────────────────────
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
TW_TZ = timezone(timedelta(hours=8))

# ── 分頁名稱 ─────────────────────────────────────────
SH_INSPIRATION = "靈感庫"
SH_VIDEO_OVERVIEW = "影片總覽"
SH_TODO = "待辦"
SH_REPORT = "報表"
SH_EMPLOYEE_LOG = "日報"

# ── 操作員 → 分頁對照 ───────────────────────────────
OPERATOR_SHEETS = {
    "kai": {
        "inspiration": SH_INSPIRATION,
        "video_overview": SH_VIDEO_OVERVIEW,
    },
}
DEFAULT_OPERATOR = next(iter(OPERATOR_SHEETS), "kai")


def resolve_operator(operator=None):
    """回傳有效 operator；未知或空值時 fallback 到 DEFAULT_OPERATOR。"""
    op = (operator or "").strip().lower()
    if not op:
        return DEFAULT_OPERATOR
    return op if op in OPERATOR_SHEETS else DEFAULT_OPERATOR


def get_operator_tabs(operator=None):
    """回傳 operator 對應分頁設定（含 fallback）。"""
    return OPERATOR_SHEETS[resolve_operator(operator)]


# ── 日報看板 layout 常數（v4.0）─────────────────────
LOG_DASHBOARD_ROWS = 4
LOG_SEPARATOR_ROW = 5
LOG_HEADER_ROW = 6
LOG_DATA_START_ROW = 7

# ── GitHub Actions 雲端中繼 ──────────────────────────
GITHUB_REPO = os.environ.get("GITHUB_REPO", "pei760730/quickshot")
GITHUB_WORKFLOW = "sync-to-sheets.yml"

# ── 強制 UTF-8 輸出 ─────────────────────────────────
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 表現分類（SSoT 在 ops/lib/config.py + ops/lib/backfill.py）──
# 從 ops 導入，確保門檻定義只有一份。


def _resolve_performance_thresholds(thresholds=None):
    """正規化 pipeline.json _meta.thresholds.performance 門檻格式。"""
    default = {
        "high_A": {"retention_3s": 70, "completion_rate": 40},
        "high_B": {"views": 300000, "completion_rate": 40},
        "low": {"retention_3s_below": 40, "completion_rate_below": 15},
    }
    if not isinstance(thresholds, dict):
        return default

    merged = {
        "high_A": dict(default["high_A"]),
        "high_B": dict(default["high_B"]),
        "low": dict(default["low"]),
    }
    for key in ("high_A", "high_B", "low"):
        val = thresholds.get(key)
        if isinstance(val, dict):
            merged[key].update(val)
    return merged


def classify_performance_display(
    views=0, retention_3s=0, completion_rate=0, thresholds=None
):
    """回傳帶 emoji 的顯示用等級（給 Sheets 用）。

    門檻優先讀取 pipeline.json _meta.thresholds.performance，
    缺漏時回退預設值（對齊 ops 端預設邏輯）。
    """
    try:
        v = float(views)
    except (TypeError, ValueError):
        v = 0
    try:
        r = float(retention_3s)
    except (TypeError, ValueError):
        r = 0
    try:
        c = float(completion_rate)
    except (TypeError, ValueError):
        c = 0

    # 門檻來源：pipeline.json _meta.thresholds.performance
    # 若缺漏則回退預設值，確保與 ops 顯示規則一致。
    th = _resolve_performance_thresholds(thresholds)
    high_a = r >= th["high_A"]["retention_3s"] and c >= th["high_A"]["completion_rate"]
    high_b = v >= th["high_B"]["views"] and c >= th["high_B"]["completion_rate"]
    low = r < th["low"]["retention_3s_below"] or c < th["low"]["completion_rate_below"]

    if high_a and high_b:
        return "🟢 高（有觸及）"
    elif high_a:
        return "🟡 留存高（觀看低）"
    elif high_b:
        return "🟢 高（有觸及）"
    elif low:
        return "🔴 低"
    return "🟡 普通"
