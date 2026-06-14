#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 驗證 + 遷移（schema 補齊）。
"""

import re
from datetime import datetime

from . import config as _cfg
from .config import (
    PROJECT_ROOT, REQUIRED_FIELDS_BY_SOURCE,
)
from .pipeline import _get_vid_assignment_statuses, _get_backfill_due_days
from .backfill import classify_performance, load_performance_patterns

# 已廢棄欄位清單（新增時只需在此列表加一筆）
DEPRECATED_FIELDS = ("hard_gates_result", "hold_reason")


def _validate_structure(data, prefix):
    errors = []
    warnings = []
    seen_vids = set()
    vid_pattern = re.compile(rf"^{re.escape(prefix)}-\d{{3,}}$")

    for i, v in enumerate(data["videos"]):
        vid = v.get("vid", f"(index {i})")
        if not vid_pattern.match(vid):
            errors.append(f"{vid}：VID 格式錯誤（應為 {prefix}-NNN）")
        if vid in seen_vids:
            errors.append(f"{vid}：重複的影片碼")
        seen_vids.add(vid)

        status = v.get("status")
        if status not in _get_vid_assignment_statuses(data):
            errors.append(f"{vid}：非法狀態 '{status}'")

        for field in ["topic", "tags"]:
            if not v.get(field):
                errors.append(f"{vid}：缺少必填欄位 {field}")

        vid_source = v.get("source")
        if vid_source:
            required = REQUIRED_FIELDS_BY_SOURCE.get(vid_source, {})
            for key in required:
                if key in ("topic", "tag"):
                    continue
                if not v.get(key):
                    errors.append(f"{vid}：[{vid_source}] 缺少 {key}")
        else:
            warnings.append(f"{vid}：缺少 source 欄位（舊記錄，建議跑 migrate 補齊）")

        for dep_field in DEPRECATED_FIELDS:
            if dep_field in v:
                errors.append(f"{vid}：包含已廢棄欄位 '{dep_field}'（應移除）")
    return errors, warnings


def _validate_values(data):
    errors = []
    warnings = []
    for i, v in enumerate(data["videos"]):
        vid = v.get("vid", f"(index {i})")
        status = v.get("status")

        if status == "已上線" and not v.get("publish_date"):
            errors.append(f"{vid}：已上線但缺少 publish_date")

        bf = v.get("backfill")
        if bf:
            for pct_field in ("retention_3s", "completion_rate", "engagement_rate"):
                val = bf.get(pct_field)
                if val is not None:
                    try:
                        fv = float(val)
                        if fv < 0 or fv > 100:
                            errors.append(f"{vid}：backfill.{pct_field}={val} 超出 0-100% 範圍")
                    except (TypeError, ValueError):
                        errors.append(f"{vid}：backfill.{pct_field}={val} 非數值")
            views_val = bf.get("views")
            if views_val is not None:
                try:
                    iv = int(views_val)
                    if iv < 0:
                        errors.append(f"{vid}：backfill.views={views_val} 不可為負數")
                except (TypeError, ValueError):
                    errors.append(f"{vid}：backfill.views={views_val} 非整數")

        if v.get("verifier_prediction") and not v.get("verifier_scores"):
            warnings.append(f"{vid}：有 verifier_prediction 但缺少 verifier_scores 細項")
    return errors, warnings


def _validate_references(data):
    errors = []
    for i, v in enumerate(data["videos"]):
        vid = v.get("vid", f"(index {i})")
        status = v.get("status")

        val = v.get("publish_date")
        if val:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                errors.append(f"{vid}：publish_date 日期無效 '{val}'（應為 YYYY-MM-DD）")

        cd = v.get("created_date")
        if not cd:
            errors.append(f"{vid}：缺少 created_date")
        else:
            try:
                datetime.strptime(cd, "%Y-%m-%d")
            except ValueError:
                errors.append(f"{vid}：created_date 日期無效 '{cd}'")

        sh = v.get("status_history")
        if not sh or not isinstance(sh, list):
            errors.append(f"{vid}：缺少 status_history")
        else:
            if sh[-1].get("status") != status:
                errors.append(f"{vid}：status_history 最後一筆 '{sh[-1].get('status')}' 與 status '{status}' 不一致")
            prev_date = None
            for entry_idx, entry in enumerate(sh):
                d = entry.get("date", "")
                if not d:
                    continue
                try:
                    parsed = datetime.strptime(d, "%Y-%m-%d")
                    if prev_date and parsed < prev_date:
                        errors.append(f"{vid}：status_history 日期倒序（第 {entry_idx} 筆 {d} 早於前一筆）")
                        break
                    prev_date = parsed
                except ValueError:
                    errors.append(f"{vid}：status_history 第 {entry_idx} 筆日期格式無效 '{d}'")
    return errors


def validate(data, warnings=None, vid_prefix=None):
    """驗證 video-tracking.json 完整性，回傳 errors 列表。"""
    prefix = vid_prefix or _cfg.get_operator_paths().get("vid_prefix", "VID")
    if warnings is None:
        warnings = []
    errors = []
    struct_errors, struct_warnings = _validate_structure(data, prefix)
    value_errors, value_warnings = _validate_values(data)
    ref_errors = _validate_references(data)
    errors.extend(struct_errors)
    errors.extend(value_errors)
    errors.extend(ref_errors)
    warnings.extend(struct_warnings)
    warnings.extend(value_warnings)
    return errors


def migrate(data):
    """補齊歷史影片缺少的 schema 欄位。冪等設計。"""
    from datetime import datetime, timedelta
    changes = []

    for v in data["videos"]:
        vid = v.get("vid", "?")
        vid_source = v.get("source", "pipeline")
        is_pre_system = (v.get("notes") or "").startswith("系統前上線") or v.get("script_path") == "系統前上線"

        if "source" not in v:
            v["source"] = "pipeline"
            changes.append({"vid": vid, "field": "source", "value": "pipeline"})
            vid_source = "pipeline"

        if "script_status" not in v:
            v["script_status"] = None
            changes.append({"vid": vid, "field": "script_status", "value": None})

        if not v.get("title"):
            v["title"] = v.get("topic", vid)
            changes.append({"vid": vid, "field": "title", "value": v["title"]})

        if vid_source == "pipeline" and not v.get("skill_used"):
            if is_pre_system:
                v["skill_used"] = "系統前上線"
            else:
                v["skill_used"] = "generation"
            changes.append({"vid": vid, "field": "skill_used", "value": v["skill_used"]})

        # 補齊 backfill_due_date（已上線且有 publish_date 的影片）
        if "backfill_due_date" not in v and v.get("status") == "已上線" and v.get("publish_date"):
            try:
                pub_dt = datetime.strptime(v["publish_date"], "%Y-%m-%d")
                v["backfill_due_date"] = (pub_dt + timedelta(days=_get_backfill_due_days(data))).strftime("%Y-%m-%d")
                changes.append({"vid": vid, "field": "backfill_due_date", "value": v["backfill_due_date"]})
            except ValueError:
                v["backfill_due_date"] = None

    return {"migrated": changes}


def check_migrate_needed(video_data):
    """檢查有多少影片可以跑 migrate 補齊欄位。回傳 list of (vid, missing_fields)。"""

    candidates = []
    for v in video_data.get("videos", []):
        vid = v.get("vid", "?")
        missing = []
        if "source" not in v:
            missing.append("source")
        if "script_status" not in v:
            missing.append("script_status")
        if not v.get("title"):
            missing.append("title")
        src = v.get("source", "pipeline")
        if src == "pipeline" and not v.get("skill_used"):
            missing.append("skill_used")
        if "backfill_due_date" not in v and v.get("status") == "已上線" and v.get("publish_date"):
            missing.append("backfill_due_date")
        if missing:
            candidates.append((vid, missing))
    return candidates


def validate_all(video_data):
    """跨檔驗證：pipeline.json + performance-patterns.json 的內部完整性 + 交叉引用一致性。"""
    if not isinstance(video_data, dict):
        return {
            "errors": ["pipeline.json 結構錯誤：根節點必須是 object"],
            "warnings": [],
            "migrate_candidates": [],
        }

    if "videos" not in video_data:
        return {
            "errors": ["pipeline.json 結構錯誤：缺少 videos 陣列"],
            "warnings": [],
            "migrate_candidates": [],
        }

    if not isinstance(video_data.get("videos"), list):
        actual_type = type(video_data.get("videos")).__name__
        return {
            "errors": [f"pipeline.json 結構錯誤：videos 應為陣列，實際為 {actual_type}"],
            "warnings": [],
            "migrate_candidates": [],
        }

    errors = []
    warnings = []

    video_errors = validate(video_data, warnings=warnings)
    errors.extend(video_errors)

    valid_vids = {v["vid"] for v in video_data["videos"]}

    # ── performance-patterns → VID 引用 ──
    pdata = load_performance_patterns()

    for category in ("proven_openings", "proven_ctas"):
        for item in pdata.get(category, []):
            code = item.get("code", "?")
            for vid in item.get("vid_evidence", []):
                if vid not in valid_vids:
                    errors.append(f"performance-patterns {category}：{code} 引用 {vid}，但該 VID 不存在")

    for formula in pdata.get("proven_formulas", []):
        # 支援新格式 vid_evidence 陣列 + 舊格式 vid 字串
        for vid in formula.get("vid_evidence", []):
            if vid and vid not in valid_vids:
                errors.append(f"performance-patterns proven_formulas：引用 {vid}，但該 VID 不存在")
        old_vid = formula.get("vid")
        if old_vid and "vid_evidence" not in formula and old_vid not in valid_vids:
            errors.append(f"performance-patterns proven_formulas：引用 {old_vid}，但該 VID 不存在")

    for rp in pdata.get("risk_patterns", []):
        vid = rp.get("vid")
        if vid and vid not in valid_vids:
            errors.append(f"performance-patterns risk_patterns：引用 {vid}，但該 VID 不存在")

    # ── 交叉一致性 ──
    for v in video_data["videos"]:
        vid = v["vid"]
        bf = v.get("backfill")

        if (
            bf
            and bf.get("learning_extracted")
            and not v.get("learning")
            and bf.get("performance") != "normal"
        ):
            warnings.append(f"{vid}：learning_extracted=true 但缺少 learning 欄位（歷史資料，建議補 extract-learning）")

        if bf and "views" in bf and "retention_3s" in bf and "completion_rate" in bf:
            recalc_level, _, _ = classify_performance(
                bf["views"], bf["retention_3s"], bf["completion_rate"],
                meta=video_data.get("_meta"),
            )
            stored_level = bf.get("performance")
            if recalc_level != stored_level:
                errors.append(
                    f"{vid}：backfill performance 存 '{stored_level}' 但門檻重算為 '{recalc_level}'"
                    f"（views={bf['views']}, retention={bf['retention_3s']}%, completion={bf['completion_rate']}%）"
                )

    # ── proven_openings/ctas 重複 code ──
    for category in ("proven_openings", "proven_ctas"):
        codes = [item["code"] for item in pdata.get(category, []) if "code" in item]
        seen = set()
        for c in codes:
            if c in seen:
                errors.append(f"performance-patterns {category}：重複 code '{c}'")
            seen.add(c)

    # ── script_path 存在性檢查 ──
    for v in video_data["videos"]:
        sp = v.get("script_path")
        if sp and sp != "系統前上線":
            full_path = PROJECT_ROOT / sp
            if not full_path.exists():
                warnings.append(f"{v['vid']}：script_path 指向 {sp}，但檔案不存在")

    # ── migrate 建議偵測 ──
    migrate_candidates = check_migrate_needed(video_data)

    return {"errors": errors, "warnings": warnings, "migrate_candidates": migrate_candidates}
