#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共用路徑、常數、時區設定。
所有模組從此處匯入，單一修改點。

OPERATORS 從 data/.operators.json 動態載入。引擎層提供 DEFAULT_OPERATORS
作為 fallback（registry 不存在時的初始值）。
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 路徑 ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ── 多操作員支援（v4.38 動態化）──────────────────────────
# 客戶 repo 的 operator 定義存在 data/.operators.json（blacklist 保護）。
# 引擎層只保留 DEFAULT_OPERATORS（kai）作為 fallback。
# 新客戶 bootstrap-client.sh 會寫入 data/.operators.json 註冊自己的 operator。

DEFAULT_OPERATORS = {
    "kai": {
        "data_dir_rel": "data/kai",
        "vid_prefix": "VID",
        "idea_prefix": "IDEA",
        "production_subdir": "kai",
        "label": "Kai",
        "brain_path": "01-data-brain/index.md",
    },
}

_OPERATORS_JSON = PROJECT_ROOT / "data" / ".operators.json"


def _resolve_operator_cfg(cfg, op_id):
    """把 rel path 轉絕對、補預設值。"""
    label = cfg.get("label") or cfg.get("display_name") or op_id.title()
    production_subdir = cfg.get("production_subdir", op_id)
    if "production_dir_rel" in cfg:
        # 新 schema 用 production_dir_rel 表示 production root。
        # 對 video-ops 而言仍需 subdir，維持與 operator id 一致。
        production_subdir = op_id
    return {
        "data_dir": PROJECT_ROOT / cfg.get("data_dir_rel", f"data/{op_id}"),
        "vid_prefix": cfg.get("vid_prefix", "VID"),
        "idea_prefix": cfg.get("idea_prefix", "IDEA"),
        "production_subdir": production_subdir,
        "label": label,
        "brain_path": cfg.get("brain_path", "01-data-brain/index.md"),
    }


def _validate_operators_payload(raw):
    if not isinstance(raw, dict):
        raise ValueError("data/.operators.json 格式錯誤：root 必須是 object")
    operators = raw.get("operators")
    if not isinstance(operators, dict):
        raise ValueError("data/.operators.json 格式錯誤：operators 必須是 object")
    # 空 operators 是合法 template state（客戶尚未 onboard）、不報錯
    for op_id, cfg in operators.items():
        if not isinstance(op_id, str) or not op_id:
            raise ValueError(
                "data/.operators.json 格式錯誤：operator key 必須是非空字串"
            )
        if not isinstance(cfg, dict):
            raise ValueError(
                f"data/.operators.json 格式錯誤：operators.{op_id} 必須是 object"
            )
        if "enabled" in cfg and not cfg.get("enabled", True):
            continue
        if "data_dir_rel" not in cfg:
            raise ValueError(
                f"data/.operators.json 格式錯誤：operators.{op_id} 缺 data_dir_rel"
            )


def _load_operators():
    """
    載入 OPERATORS 定義：
    - 若 data/.operators.json 存在 → 以其為準（blacklist 保護、客戶端 bootstrap 寫入）
    - 否則 → DEFAULT_OPERATORS（引擎層 fallback）
    """
    if not _OPERATORS_JSON.exists():
        return {
            op_id: _resolve_operator_cfg(cfg, op_id)
            for op_id, cfg in DEFAULT_OPERATORS.items()
        }
    raw = json.loads(_OPERATORS_JSON.read_text(encoding="utf-8"))
    _validate_operators_payload(raw)
    result = {}
    for op_id, cfg in raw.get("operators", {}).items():
        if cfg.get("enabled", True):
            result[op_id] = _resolve_operator_cfg(cfg, op_id)
    if not result:
        # 空 operators 是合法 template state（客戶尚未 onboard）、fallback DEFAULT
        return {
            op_id: _resolve_operator_cfg(cfg, op_id)
            for op_id, cfg in DEFAULT_OPERATORS.items()
        }
    return result


OPERATORS = _load_operators()
DEFAULT_OPERATOR = "kai" if "kai" in OPERATORS else next(iter(OPERATORS), "kai")
VALID_OPERATORS = set(OPERATORS.keys())


def get_operator_paths(operator=None):
    """回傳指定操作員的 JSON 路徑 dict。

    回傳：
    {
        "pipeline_json": Path,
        "performance_patterns_json": Path,
        "data_dir": Path,
        "vid_prefix": str,
        "label": str,
        "operator": str,
    }
    """
    if operator is None:
        operator = globals().get("_current_operator", DEFAULT_OPERATOR)
    operator = operator.lower()
    if operator not in OPERATORS:
        raise ValueError(
            f"未知操作員：{operator}（合法值：{', '.join(sorted(VALID_OPERATORS))}）"
        )
    cfg = OPERATORS[operator]
    data_dir = cfg["data_dir"]
    return {
        "pipeline_json": data_dir / "pipeline.json",
        "pipeline": data_dir / "pipeline.json",
        "performance_patterns_json": data_dir / "performance-patterns.json",
        "performance_patterns": data_dir / "performance-patterns.json",
        "brand_monitor": data_dir / "brand-monitor.json",
        "todos": data_dir / "todos.json",
        "data_dir": data_dir,
        "vid_prefix": cfg["vid_prefix"],
        "idea_prefix": cfg["idea_prefix"],
        "production_subdir": cfg["production_subdir"],
        "label": cfg["label"],
        "operator": operator,
    }


# 向後相容：預設路徑指向 DEFAULT_OPERATOR
_default_paths = get_operator_paths(DEFAULT_OPERATOR)
PIPELINE_JSON = _default_paths["pipeline_json"]
PERFORMANCE_PATTERNS_JSON = _default_paths["performance_patterns_json"]

# 當前操作員（CLI 啟動時由 set_operator 設定）
_current_operator = DEFAULT_OPERATOR


def set_operator(operator):
    """切換當前操作員，更新所有模組級路徑常數。

    必須在 CLI 啟動時、任何 load/save 操作前呼叫。
    """
    global PIPELINE_JSON, PERFORMANCE_PATTERNS_JSON
    global _current_operator
    operator = operator.lower()
    if operator not in OPERATORS:
        raise ValueError(
            f"未知操作員：{operator}（合法值：{', '.join(sorted(VALID_OPERATORS))}）"
        )
    paths = get_operator_paths(operator)
    PIPELINE_JSON = paths["pipeline_json"]
    PERFORMANCE_PATTERNS_JSON = paths["performance_patterns_json"]
    _current_operator = operator


def current_operator():
    """回傳當前操作員名稱"""
    return _current_operator


# ── 時區 ─────────────────────────────────────────────────
TW_TZ = timezone(timedelta(hours=8))


def today_str():
    return datetime.now(TW_TZ).strftime("%Y-%m-%d")


# ── 業務常數 ─────────────────────────────────────────────
# 狀態機和門檻已移入 pipeline.json _meta（資料驅動）。
# 以下僅保留程式碼仍需要的業務常數。
VALID_SOURCES = {"pipeline", "quick-shot"}

REQUIRED_FIELDS_BY_SOURCE = {
    "pipeline": {
        "topic": "主題",
        "title": "封面標題",
    },
    "quick-shot": {
        "topic": "主題",
        "title": "封面標題",
    },
}

# ── 表現門檻 ─────────────────────────────────────────────
PERFORMANCE_THRESHOLDS = {
    "high": {
        "path_A": {"retention_3s_min": 70, "completion_rate_min": 40},
        "path_B": {"views_min": 300000, "completion_rate_min": 40},
    },
    "low": {
        "retention_3s_max": 50,
        "completion_rate_max": 25,
    },
}

PERFORMANCE_DISPLAY = {
    "high_reach": "🟢 高（有觸及）",
    "high_retention": "🟡 留存高（觀看低）",
    "low": "🔴 低",
    "normal": "🟡 普通",
}


# ── 診斷門檻 ─────────────────────────────────────────────
DIAGNOSIS_THRESHOLDS = {
    "hook_weak": 55,  # retention_3s < 55% → Hook 弱
    "completion_weak": 25,  # completion_rate < 25% → 完播弱
    "engagement_weak": 1.5,  # engagement_rate < 1.5% → 互動弱
    "engagement_strong": 3.0,  # engagement_rate >= 3.0% → 互動率強
    "dud_engagement": 0.5,  # 總互動率 < 0.5% → 啞彈
    "balanced_gap": 10,  # 三者佔比差距 < 10% → 均衡型
}

# ── Pattern 門檻（衰減 + 注入）────────────────────────
PATTERN_THRESHOLDS = {
    "decay_low_evidence_trigger": 2,  # 幾支低表現影片使用此 pattern → 標記 degraded
    "injection_min_evidence": 2,  # proven_openings / proven_ctas 需幾支影片才注入腳本
    "formula_injection_min": 1,  # proven_formulas 只要 1 支就注入
    "confidence_medium_min": 3,  # total_uses >= 3 → medium confidence
    "confidence_high_min": 8,  # total_uses >= 8 → high confidence
}
