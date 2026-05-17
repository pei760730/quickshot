#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一管線 CRUD + 狀態機（pipeline.json SSoT）。

一個選題從靈感到上線，同一筆資料、同一個檔案。
靈感階段用 IDEA-NNN，確認要拍時分配 VID-NNN。
"""

import glob
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from . import config as _cfg
from .config import (
    VALID_SOURCES,
    REQUIRED_FIELDS_BY_SOURCE,
    PROJECT_ROOT,
    today_str,
)
from .storage import load_json, save_json


def _pipeline_paths(pipeline_json=None):
    legacy = Path(pipeline_json or _cfg.PIPELINE_JSON)
    root = legacy.parent / "pipeline"
    meta_path = root / "_meta.json"
    items_dir = root / "items"
    return legacy, root, meta_path, items_dir


def _item_key(item):
    return item.get("vid") or item.get("idea_id") or ""


def _read_pipeline_sharded(pipeline_json=None):
    legacy, _, meta_path, items_dir = _pipeline_paths(pipeline_json)
    if not meta_path.exists() or not items_dir.exists():
        return None, legacy
    meta = load_json(str(meta_path), {}, str(meta_path))
    items = []
    for p in sorted(items_dir.glob("*.json")):
        item = load_json(str(p), {}, str(p))
        if isinstance(item, dict) and item.get("idea_id"):
            items.append(item)
    items.sort(key=_item_key)
    return {"_meta": meta, "items": items}, legacy


def get_pipeline_data(pipeline_json=None):
    """Pure read from sharded pipeline data with no side effect.

    Returns {"_meta": dict, "items": list} when sharded data exists, or None
    when it does not. Will replace load_pipeline() in Phase 4.
    """
    data, _ = _read_pipeline_sharded(pipeline_json=pipeline_json)
    return data


def _load_pipeline_sharded(pipeline_json=None):
    data, _ = _read_pipeline_sharded(pipeline_json=pipeline_json)
    return data

# ── 向後相容 fallback（_meta 缺失時使用）────────────────
_FALLBACK_STATUSES = {
    "inbox", "selected", "cooldown",
    "待拍", "剪輯中", "已上線",
    "archived",
}
_FALLBACK_TRANSITIONS = {
    "inbox": ["selected", "cooldown", "archived"],
    "selected": ["待拍", "cooldown", "archived"],
    "cooldown": ["inbox", "selected", "archived"],
    "待拍": ["剪輯中"],
    "剪輯中": ["已上線"],
    "已上線": [],
    "archived": ["inbox"],
}
_FALLBACK_VID_STATUSES = {"待拍", "剪輯中", "已上線"}

def _load_meta(data):
    """讀取並補齊 _meta schema，回傳標準化 meta dict。"""
    meta = data.setdefault("_meta", {})
    statuses = meta.setdefault("statuses", {})
    if "idea" not in statuses:
        statuses["idea"] = ["inbox", "selected", "cooldown", "archived"]
    if "video" not in statuses:
        statuses["video"] = sorted(_FALLBACK_VID_STATUSES)

    transitions = meta.setdefault("transitions", {})
    if not transitions:
        meta["transitions"] = dict(_FALLBACK_TRANSITIONS)
        transitions = meta["transitions"]

    thresholds = meta.setdefault("thresholds", {})
    thresholds.setdefault("backfill_due_days", 3)
    thresholds.setdefault("performance", {
        "high": {"retention_3s_gte": 70, "completion_rate_gte": 40, "views_gte": 300000},
        "low": {"retention_3s_lt": 40, "completion_rate_lt": 15},
    })

    meta.setdefault("sedimentation", {
        "max_proposals_per_backfill": 2,
        "fallback_threshold": 3,
    })
    meta.setdefault("quality", {
        "levels": {
            "L0": {"pass_count": "5/5", "max_ai_residue_count": 0, "min_conflict_score": 7},
            "L1": {"pass_count": "4/5", "max_ai_residue_count": 1, "min_conflict_score": 5},
            "L2": {"pass_count": "3/5", "max_ai_residue_count": 2, "min_conflict_score": 4},
        }
    })
    meta.setdefault("verifier", {
        "checks": {
            "conflict_score_min": 4,
            "ai_residue_count_min": 1,
            "data_consistency_required": True,
            "format_complete_required": True,
            "pass_count_min_ratio": "3/5",
        }
    })

    if not isinstance(meta.get("next_idea_id"), int):
        max_idea = 0
        prefix = _cfg.get_operator_paths().get("idea_prefix", "IDEA")
        for item in data.get("items", []):
            m = re.match(rf"^{re.escape(prefix)}-(\d+)$", item.get("idea_id", ""))
            if m:
                max_idea = max(max_idea, int(m.group(1)))
        meta["next_idea_id"] = max_idea + 1
    if not isinstance(meta.get("next_vid"), int):
        max_vid = 0
        prefix = _cfg.get_operator_paths().get("vid_prefix", "VID")
        for item in data.get("items", []):
            m = re.match(rf"^{re.escape(prefix)}-(\d+)$", item.get("vid", ""))
            if m:
                max_vid = max(max_vid, int(m.group(1)))
        meta["next_vid"] = max_vid + 1
    return meta


def _get_all_statuses(data):
    meta = _load_meta(data)
    result = set()
    for vals in meta.get("statuses", {}).values():
        result.update(vals)
    return result or _FALLBACK_STATUSES


def _get_transitions(data):
    return _load_meta(data).get("transitions", _FALLBACK_TRANSITIONS)


def _get_vid_assignment_statuses(data):
    meta = _load_meta(data)
    video_statuses = meta.get("statuses", {}).get("video", [])
    return set(video_statuses or _FALLBACK_VID_STATUSES)


def _get_backfill_due_days(data):
    return _load_meta(data).get("thresholds", {}).get("backfill_due_days", 3)


def _status_script_stage(status):
    """將影片狀態映射到腳本所在階段資料夾。"""
    return "done" if status == "已上線" else "ready"


def _remap_script_stage_path(script_path, target_stage):
    """依目標階段回傳新的 script_path；無法判斷時回傳 None。"""
    if "02-ready-to-shoot/" in script_path:
        return script_path.replace("02-ready-to-shoot/", "03-done/") if target_stage == "done" else script_path
    if "03-done/" in script_path:
        return script_path.replace("03-done/", "02-ready-to-shoot/") if target_stage == "ready" else script_path
    return None


# ---------------------------------------------------------------------------
# 向後相容：以下別名讓 backfill / validate / video-ops 等消費者
# 可以直接用 pipeline 格式的資料結構操作影片。
#
# 資料格式：
#   data["items"]  — 所有項目（靈感 + 影片）
#   item["tags"]   — 標籤（不是 "tag"）
#   item["vid"]    — VID-NNN 或 None（靈感階段）
#
# "videos" 視圖：filter items where vid is not None
# ---------------------------------------------------------------------------


# ── 載入 / 儲存 ──────────────────────────────────────────

def load_pipeline(pipeline_json=None):
    """Backward-compatible alias for pure sharded pipeline reads."""
    return get_pipeline_data(pipeline_json=pipeline_json)


def _validate_for_save(data):
    """save_pipeline / save_tracking 共用的寫前驗證邏輯。

    收集結構 / 格式 / 去重錯誤，出錯則 raise ValueError。抽出獨立函式便於
    測試、複用，以及日後若需「只驗證不寫入」時直接呼叫。
    """
    errors = []
    seen_idea_ids = set()
    seen_vids = set()
    idea_prefix = _cfg.get_operator_paths().get("idea_prefix", "IDEA")
    idea_pattern = re.compile(rf"^{re.escape(idea_prefix)}-\d{{3,}}$")
    vid_prefix = _cfg.get_operator_paths().get("vid_prefix", "VID")
    vid_pattern = re.compile(rf"^{re.escape(vid_prefix)}-\d{{3,}}$")

    all_statuses = _get_all_statuses(data)
    video_statuses = _get_vid_assignment_statuses(data)
    for i, item in enumerate(data.get("items", [])):
        iid = item.get("idea_id", f"(index {i})")
        if not idea_pattern.match(iid):
            errors.append(f"{iid}：IDEA-ID 格式錯誤（應為 {idea_prefix}-NNN）")
        if iid in seen_idea_ids:
            errors.append(f"{iid}：重複的 IDEA-ID")
        seen_idea_ids.add(iid)

        vid = item.get("vid")
        if vid:
            if not vid_pattern.match(vid):
                errors.append(f"{iid}：VID 格式錯誤 '{vid}'（應為 {vid_prefix}-NNN）")
            if vid in seen_vids:
                errors.append(f"{iid}：重複的 VID '{vid}'")
            seen_vids.add(vid)

        status = item.get("status")
        if status not in all_statuses:
            errors.append(f"{iid}：非法狀態 '{status}'")
        if status in video_statuses and not vid:
            errors.append(f"{iid}：狀態 '{status}' 但缺少 VID")
        if not item.get("created_date"):
            errors.append(f"{iid}：缺少 created_date")
        sl = item.get("shelf_life")
        if sl is not None and sl not in VALID_SHELF_LIVES:
            errors.append(f"{iid}：非法 shelf_life '{sl}'（合法值：{', '.join(sorted(VALID_SHELF_LIVES))}）")

    if errors:
        raise ValueError(
            f"寫前驗證失敗（{len(errors)} 個錯誤）：\n  " + "\n  ".join(errors)
        )


def save_pipeline(data, skip_validate=False, pipeline_json=None):
    """寫入 sharded pipeline（寫前自動驗證）。"""
    meta = _load_meta(data)
    if not skip_validate:
        _validate_for_save(data)
    data["_meta"] = meta
    _path, _root, meta_path, items_dir = _pipeline_paths(pipeline_json)
    items_dir.mkdir(parents=True, exist_ok=True)
    save_json(str(meta_path), meta)
    keep = set()
    for item in data.get("items", []):
        idea_id = item.get("idea_id")
        if not idea_id:
            continue
        vid = item.get("vid")
        filename = f"{vid}.json" if vid else f"{idea_id}.json"
        keep.add(filename)
        save_json(str(items_dir / filename), item)
    for old in items_dir.glob("*.json"):
        if old.name not in keep:
            old.unlink()
    data["items"].sort(key=_item_key)


# ── 查找 ──────────────────────────────────────────────────

def find_by_idea_id(data, idea_id):
    """依 IDEA-ID 查找，回傳 (index, item) 或 (None, None)"""
    for i, item in enumerate(data["items"]):
        if item["idea_id"] == idea_id:
            return i, item
    return None, None


def find_by_vid(data, vid):
    """依 VID 查找，回傳 (index, item) 或 (None, None)"""
    for i, item in enumerate(data["items"]):
        if item.get("vid") == vid:
            return i, item
    return None, None


def find_item(data, identifier):
    """依 IDEA-NNN 或 VID-NNN 查找（自動判斷）"""
    if identifier.startswith(("VID-", "RBY-")):
        return find_by_vid(data, identifier)
    return find_by_idea_id(data, identifier)


# ── 編號管理 ──────────────────────────────────────────────

def next_idea_id(data, idea_prefix=None):
    """取得下一個 IDEA-NNN"""
    prefix = idea_prefix or _cfg.get_operator_paths().get("idea_prefix", "IDEA")
    cached = _load_meta(data).get("next_idea_id", 1)
    return f"{prefix}-{int(cached):03d}"


def next_vid(data, vid_prefix=None):
    """取得下一個 VID-NNN"""
    prefix = vid_prefix or _cfg.get_operator_paths().get("vid_prefix", "VID")
    cached = _load_meta(data).get("next_vid", 1)
    return f"{prefix}-{int(cached):03d}"


def _bump_next_idea_id(data, idea_id):
    m = re.match(r"^[A-Z]+-(\d+)$", idea_id)
    if m:
        data.setdefault("_meta", {})["next_idea_id"] = int(m.group(1)) + 1


def _bump_next_vid(data, vid):
    m = re.match(r"^[A-Z]+-(\d+)$", vid)
    if m:
        data.setdefault("_meta", {})["next_vid"] = int(m.group(1)) + 1


# ── 靈感時效性 ────────────────────────────────────────────
VALID_SHELF_LIVES = {"evergreen", "timely", "trending"}

GEN_TRACE_REQUIRED_FIELDS = [
    "skill_used",
    "skill_version",
    "generated_at",
    "title_type",
    "hook_type",
    "version_chosen",
]
GEN_TRACE_OPTIONAL_FIELDS = [
    "patterns_injected",
    "risk_patterns_avoided",
    "persona_deviation_score",
    "verifier_prediction",
    "lessons_referenced",
]
GEN_TRACE_ALLOWED_FIELDS = set(GEN_TRACE_REQUIRED_FIELDS + GEN_TRACE_OPTIONAL_FIELDS)


def classify_idea_freshness(item, thresholds, today=None):
    """判斷靈感新鮮度，回傳 (label, sort_key)。

    label: "expired" | "stale" | "fresh"
    sort_key: 數字越小越靠前（用於排序）

    排序邏輯（小 → 大）：
      0 = 🔥 trending fresh
      1 = 🕐 timely fresh
      2 = 一般 (evergreen / null) fresh
      3 = ⏰ stale (任何 shelf_life)
      4 = ⚠️ expired
    """
    if today is None:
        today = datetime.strptime(today_str(), "%Y-%m-%d")
    created = datetime.strptime(item.get("created_date", today_str()),
                                "%Y-%m-%d")
    age_days = (today - created).days
    sl = item.get("shelf_life")

    stale_map = thresholds.get("shelf_life_stale_days", {})
    expire_map = thresholds.get("shelf_life_expire_days", {})

    # 有 expire 門檻且超過 → expired
    if sl in expire_map and age_days > expire_map[sl]:
        return "expired", 4
    # timely 沒有 expire 門檻，用 stale × 2 當 expire
    if sl == "timely" and sl in stale_map and age_days > stale_map[sl] * 2:
        return "expired", 4
    # 有 stale 門檻且超過 → stale
    if sl in stale_map and age_days > stale_map[sl]:
        return "stale", 3

    # fresh — 按 shelf_life 排優先級
    priority = {"trending": 0, "timely": 1}.get(sl, 2)
    return "fresh", priority


# ── 新增 ──────────────────────────────────────────────────

def add_item(data, topic, tags="", notes=None, shelf_life=None,
             pipeline_json=None):
    """新增一筆到管線（進入 inbox），回傳 IDEA-NNN。"""
    if shelf_life and shelf_life not in VALID_SHELF_LIVES:
        raise ValueError(
            f"非法 shelf_life：{shelf_life}（合法值：{', '.join(sorted(VALID_SHELF_LIVES))}）"
        )
    idea_id = next_idea_id(data)
    _bump_next_idea_id(data, idea_id)
    td = today_str()
    if tags:
        tags = tags.replace(",", " ")
    item = {
        "idea_id": idea_id,
        "vid": None,
        "topic": topic,
        "tags": tags,
        "title": None,
        "status": "inbox",
        "created_date": td,
        "status_history": [{"status": "inbox", "date": td}],
        "publish_date": None,
        "script_path": None,
        "source": "pipeline",
        "source_inspiration": topic,
        "skill_used": None,
        "script_status": None,
        "notes": notes,
        "backfill": None,
        "shelf_life": shelf_life,
    }
    data["items"].append(item)
    save_pipeline(data, pipeline_json=pipeline_json)
    return idea_id


# ── 狀態轉換（核心）──────────────────────────────────────

def transition_item(data, identifier, new_status, title=None,
                    skill_used=None, source_inspiration=None,
                    pipeline_json=None):
    """統一狀態轉換。

    當從 selected → 待拍 時自動分配 VID（確認要拍）。
    回傳 (success, message, vid_assigned)。
    """
    idx, item = find_item(data, identifier)
    if item is None:
        return False, f"找不到 {identifier}", None

    current = item["status"]
    if new_status not in _get_all_statuses(data):
        return False, f"非法狀態：{new_status}", None

    allowed = _get_transitions(data).get(current, [])
    if new_status not in allowed:
        return (
            False,
            f"禁止的跳轉：{current} → {new_status}（允許：{', '.join(allowed) if allowed else '無'}）",
            None,
        )

    vid_assigned = None

    # 進入影片階段時自動分配 VID
    if new_status in _get_vid_assignment_statuses(data) and not item.get("vid"):
        vid = next_vid(data)
        _bump_next_vid(data, vid)
        item["vid"] = vid
        vid_assigned = vid

    # 更新可選欄位
    if title:
        item["title"] = title
    if skill_used:
        item["skill_used"] = skill_used
    if source_inspiration:
        item["source_inspiration"] = source_inspiration

    # 更新狀態
    item["status"] = new_status
    td = today_str()
    item["status_history"].append({"status": new_status, "date": td})

    if new_status == "已上線" and not item.get("publish_date"):
        item["publish_date"] = td

    data["items"][idx] = item
    save_pipeline(data, pipeline_json=pipeline_json)

    msg = f"{identifier}：{current} → {new_status}"
    if vid_assigned:
        msg += f"（已分配 {vid_assigned}）"

    return True, msg, vid_assigned


# ── 查詢 ──────────────────────────────────────────────────

def pipeline_stats(data):
    """計算轉化漏斗統計。回傳 dict 包含各階段數量、轉化率、平均週期。"""
    items = data.get("items", [])
    from collections import Counter

    # 階段計數
    status_counts = Counter(i["status"] for i in items)

    total_ideas = len(items)
    has_vid = [i for i in items if i.get("vid")]
    published = [i for i in items if i["status"] == "已上線"]
    backfilled = [i for i in items if i.get("backfill")]
    archived = [i for i in items if i["status"] == "archived"]

    # 轉化率
    idea_to_vid = len(has_vid) / total_ideas * 100 if total_ideas else 0
    vid_to_publish = len(published) / len(has_vid) * 100 if has_vid else 0
    idea_to_publish = len(published) / total_ideas * 100 if total_ideas else 0

    # 平均週期（從 created_date 到 publish_date）
    cycle_days = []
    for i in published:
        cd = i.get("created_date")
        pd = i.get("publish_date")
        if cd and pd:
            try:
                d_created = datetime.strptime(cd, "%Y-%m-%d")
                d_published = datetime.strptime(pd, "%Y-%m-%d")
                delta = (d_published - d_created).days
                if delta >= 0:
                    cycle_days.append(delta)
            except ValueError:
                pass
    avg_cycle = sum(cycle_days) / len(cycle_days) if cycle_days else None

    # 瓶頸：待拍中等待最久的
    waiting = [i for i in items if i["status"] == "待拍"]
    longest_wait = None
    if waiting:
        td = today_str()
        today_dt = datetime.strptime(td, "%Y-%m-%d")
        waits = []
        for i in waiting:
            cd = i.get("created_date")
            if cd:
                try:
                    waits.append((i, (today_dt - datetime.strptime(cd, "%Y-%m-%d")).days))
                except ValueError:
                    pass
        if waits:
            waits.sort(key=lambda x: -x[1])
            top = waits[0]
            longest_wait = {"vid": top[0].get("vid") or top[0]["idea_id"],
                            "topic": top[0]["topic"], "days": top[1]}

    return {
        "total_ideas": total_ideas,
        "status_counts": dict(status_counts),
        "has_vid": len(has_vid),
        "published": len(published),
        "backfilled": len(backfilled),
        "archived": len(archived),
        "idea_to_vid_pct": round(idea_to_vid, 1),
        "vid_to_publish_pct": round(vid_to_publish, 1),
        "idea_to_publish_pct": round(idea_to_publish, 1),
        "avg_cycle_days": round(avg_cycle, 1) if avg_cycle is not None else None,
        "cycle_sample_size": len(cycle_days),
        "longest_wait": longest_wait,
    }


# ── 向後相容別名 ─────────────────────────────────────────────

def load_tracking(tracking_json=None):
    """向後相容：載入 pipeline.json 並回傳含 ``videos`` 鍵的視圖。

    ``data["videos"]`` 是一個 *引用* 列表，指向 ``data["items"]``
    中 ``vid`` 非 None 的項目。修改 ``videos`` 中的 dict 同時也修改
    ``items`` 中的同一物件。

    為保持最小改動，每個影片 dict 也帶有 ``tag`` 鍵（指向 ``tags``
    的值），透過 ``_VideoView`` 包裝。
    """
    pipeline_data = load_pipeline(pipeline_json=tracking_json)
    videos = [item for item in pipeline_data.get("items", []) if item.get("vid")]
    return {
        "_meta": pipeline_data.get("_meta", {}),
        "videos": videos,
        "items": pipeline_data.get("items", []),
        "_pipeline_ref": pipeline_data,
    }


def save_tracking(data, skip_validate=False, tracking_json=None):
    """向後相容：儲存（實際寫 pipeline.json）。"""
    # 如果 data 本身就是 pipeline 格式（有 items，沒有 _pipeline_ref），直接存
    pipeline_data = data.get("_pipeline_ref", data)
    # 同步 _meta
    if "_meta" in data and pipeline_data is not data:
        pipeline_data["_meta"] = data["_meta"]
    save_pipeline(pipeline_data, skip_validate=skip_validate, pipeline_json=tracking_json)


def find_video(data, vid):
    """向後相容：依 VID 查找影片。

    在 ``data["videos"]`` 中搜尋。回傳 ``(index_in_videos, item)``
    或 ``(None, None)``。
    """
    videos = data.get("videos", data.get("items", []))
    for i, v in enumerate(videos):
        if v.get("vid") == vid:
            return i, v
    return None, None


def set_hook_type(data, vid, hook_type, tracking_json=None):
    """回填既有影片的 hook_type（quick-shot 存量補齊用）。

    回傳 ``(success, message)``。若 ``_meta.valid_hook_types`` 存在
    且 ``hook_type`` 不在其中，返回失敗訊息（不寫入）。
    """
    _, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"
    pipeline_data = data.get("_pipeline_ref", data)
    valid_ht = pipeline_data.get("_meta", {}).get("valid_hook_types", [])
    if valid_ht and hook_type not in valid_ht:
        return False, f"非法 hook_type：{hook_type}（合法值：{', '.join(valid_ht)}）"
    prev = video.get("hook_type")
    video["hook_type"] = hook_type
    try:
        save_tracking(data, tracking_json=tracking_json)
    except Exception:
        if prev is None:
            video.pop("hook_type", None)
        else:
            video["hook_type"] = prev
        raise
    msg_prev = f"（原 {prev}）" if prev else "（原未設）"
    return True, f"{vid} hook_type = {hook_type}{msg_prev}"


def validate_generation_trace(trace_dict, meta=None):
    """驗證 generation_trace（Learning Loop Contract v1.4）.

    回傳 (success, msg, warnings, normalized_dict)。
    """
    if not isinstance(trace_dict, dict):
        return False, "trace 必須是 JSON object", [], None

    missing = [k for k in GEN_TRACE_REQUIRED_FIELDS if k not in trace_dict]
    if missing:
        return False, f"缺少 required：{', '.join(missing)}", [], None

    normalized = dict(trace_dict)
    if not isinstance(normalized.get("skill_used"), str) or not normalized["skill_used"].strip():
        return False, "skill_used 必須為非空字串", [], None
    if not isinstance(normalized.get("skill_version"), str) or not normalized["skill_version"].strip():
        return False, "skill_version 必須為非空字串", [], None
    if not isinstance(normalized.get("generated_at"), str):
        return False, "generated_at 必須為 ISO 日期字串（YYYY-MM-DD）", [], None
    try:
        datetime.strptime(normalized["generated_at"], "%Y-%m-%d")
    except ValueError:
        return False, "generated_at 必須為 ISO 日期字串（YYYY-MM-DD）", [], None
    if not isinstance(normalized.get("title_type"), str) or not normalized["title_type"].strip():
        return False, "title_type 必須為非空字串", [], None
    if not isinstance(normalized.get("hook_type"), str) or not normalized["hook_type"].strip():
        return False, "hook_type 必須為非空字串", [], None
    if not isinstance(normalized.get("version_chosen"), str) or normalized["version_chosen"] not in {"A", "B", "C", "D"}:
        return False, "version_chosen 必須為 A/B/C/D", [], None

    if "patterns_injected" in normalized:
        val = normalized["patterns_injected"]
        if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
            return False, "patterns_injected 必須為字串陣列", [], None
    if "risk_patterns_avoided" in normalized:
        val = normalized["risk_patterns_avoided"]
        if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
            return False, "risk_patterns_avoided 必須為字串陣列", [], None
    if "persona_deviation_score" in normalized:
        val = normalized["persona_deviation_score"]
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return False, "persona_deviation_score 必須為數字", [], None
        normalized["persona_deviation_score"] = float(val)
    if "verifier_prediction" in normalized:
        val = normalized["verifier_prediction"]
        if val not in {"high", "normal", "low"}:
            return False, "verifier_prediction 必須為 high/normal/low", [], None
    if "lessons_referenced" in normalized:
        val = normalized["lessons_referenced"]
        if not isinstance(val, list) or any(not isinstance(x, str) for x in val):
            return False, "lessons_referenced 必須為字串陣列", [], None

    meta = meta or {}
    valid_ht = meta.get("valid_hook_types", [])
    if valid_ht and normalized.get("hook_type") not in valid_ht:
        return False, f"非法 hook_type：{normalized.get('hook_type')}（合法值：{', '.join(valid_ht)}）", [], None
    valid_tt = meta.get("valid_title_types", [])
    if valid_tt and normalized.get("title_type") not in valid_tt:
        return False, f"非法 title_type：{normalized.get('title_type')}（合法值：{', '.join(valid_tt)}）", [], None

    unknown = sorted(k for k in normalized.keys() if k not in GEN_TRACE_ALLOWED_FIELDS)
    warnings = [f"未知欄位（已接受）：{k}" for k in unknown]
    return True, "ok", warnings, normalized


def set_trace(data, vid, trace_dict, tracking_json=None, no_overwrite=False):
    """回填既有影片的 generation_trace（Learning Loop Contract）。"""
    _, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"
    if no_overwrite and video.get("generation_trace") is not None:
        return False, f"{vid} 已有 generation_trace（--no-overwrite）"

    pipeline_data = data.get("_pipeline_ref", data)
    meta = pipeline_data.get("_meta", {})
    ok, msg, _warnings, normalized = validate_generation_trace(trace_dict, meta=meta)
    if not ok:
        return False, msg

    prev = video.get("generation_trace")
    video["generation_trace"] = normalized
    try:
        save_tracking(data, tracking_json=tracking_json)
    except Exception:
        if prev is None:
            video.pop("generation_trace", None)
        else:
            video["generation_trace"] = prev
        raise
    return True, f"{vid} trace 已記錄 (skill={normalized['skill_used']} v={normalized['skill_version']})"


# ── 影片 CRUD（原 video.py）────────────────────────────────

def add_video(data, topic, tag, source_inspiration=None, script_path=None,
              notes=None, source="pipeline", initial_status="待拍",
              script_status=None, skill_used=None, title=None,
              vid_prefix=None, tracking_json=None, persist=True,
              hook_type=None):
    """新增一支影片到 pipeline，回傳新 VID。"""
    if initial_status not in _get_vid_assignment_statuses(data):
        raise ValueError(f"非法初始狀態：{initial_status}")
    if source not in VALID_SOURCES:
        raise ValueError(f"非法來源：{source}（合法值：{', '.join(sorted(VALID_SOURCES))}）")

    field_values = {
        "topic": topic, "tag": tag, "source_inspiration": source_inspiration,
        "skill_used": skill_used, "title": title,
    }
    required = REQUIRED_FIELDS_BY_SOURCE.get(source, {})
    missing = [f"{desc}（{key}）" for key, desc in required.items() if not field_values.get(key)]
    if missing:
        raise ValueError(f"[{source}] 缺少必填欄位：{', '.join(missing)}")

    if hook_type is not None:
        pipeline_data_for_meta = data.get("_pipeline_ref", data)
        valid_ht = pipeline_data_for_meta.get("_meta", {}).get("valid_hook_types", [])
        if valid_ht and hook_type not in valid_ht:
            raise ValueError(f"非法 hook_type：{hook_type}（合法值：{', '.join(valid_ht)}）")

    # pipeline.json 中每個項目都需要 idea_id
    pipeline_data = data.get("_pipeline_ref", data)
    idea_id = next_idea_id(pipeline_data)
    _bump_next_idea_id(pipeline_data, idea_id)

    vid = next_vid(pipeline_data, vid_prefix=vid_prefix)
    prev_next_vid = pipeline_data.get("_meta", {}).get("next_vid")
    _bump_next_vid(pipeline_data, vid)
    td = today_str()
    backfill_due = None
    if initial_status == "已上線":
        try:
            from datetime import timedelta as _td
            pub_dt = datetime.strptime(td, "%Y-%m-%d")
            backfill_due = (pub_dt + _td(days=_get_backfill_due_days(data))).strftime("%Y-%m-%d")
        except ValueError:
            pass

    video = {
        "idea_id": idea_id,
        "vid": vid,
        "topic": topic,
        "tags": tag,
        "status": initial_status,
        "created_date": td,
        "status_history": [{"status": initial_status, "date": td}],
        "publish_date": td if initial_status == "已上線" else "",
        "script_path": script_path,
        "source_inspiration": source_inspiration or topic,
        "notes": notes,
        "backfill": None,
        "backfill_due_date": backfill_due,
        "source": source,
        "script_status": script_status,
        "title": title,
        "skill_used": skill_used,
    }
    if hook_type is not None:
        video["hook_type"] = hook_type
    pipeline_data["items"].append(video)
    # 同步 videos 列表（如果存在）
    if "videos" in data and data is not pipeline_data:
        data["videos"].append(video)
    if persist:
        try:
            save_tracking(data, tracking_json=tracking_json)
        except Exception:
            pipeline_data["items"].pop()
            if "videos" in data and data is not pipeline_data and data["videos"] and data["videos"][-1] is video:
                data["videos"].pop()
            if prev_next_vid is not None:
                pipeline_data["_meta"]["next_vid"] = prev_next_vid
            else:
                pipeline_data.get("_meta", {}).pop("next_vid", None)
            raise
    return vid


def transition(data, vid, new_status, reason=None, tracking_json=None):
    """影片狀態轉換（含腳本搬移），回傳 (success, message)。"""
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"

    current = video["status"]
    if new_status not in _get_vid_assignment_statuses(data):
        return False, f"非法狀態：{new_status}（合法值：{', '.join(sorted(_get_vid_assignment_statuses(data)))}）"

    allowed = _get_transitions(data).get(current, [])
    if new_status not in allowed:
        return False, f"禁止的跳轉：{current} → {new_status}（允許：{', '.join(allowed) if allowed else '無'}）"

    if new_status == "剪輯中" and not video.get("script_path"):
        return False, f"{vid}：待拍 → 剪輯中 需要 script_path（沒有腳本不能進剪輯）"

    is_quick_shot_pending = (
        video.get("source") == "quick-shot"
        and video.get("script_status") == "待補"
    )

    if new_status == "已上線" and not is_quick_shot_pending:
        sp = video.get("script_path")
        if sp and sp != "系統前上線":
            script_file = PROJECT_ROOT / sp
            if not script_file.exists():
                return False, f"{vid}：腳本檔案不存在 {sp}"

    # 狀態跨 ready/done 邊界時先搬移腳本
    new_sp_result = None
    old_stage = _status_script_stage(current)
    new_stage = _status_script_stage(new_status)
    if old_stage != new_stage:
        sp = video.get("script_path") or ""
        new_sp = _remap_script_stage_path(sp, new_stage)
        if new_sp and new_sp != sp:
            src = PROJECT_ROOT / sp
            dst = PROJECT_ROOT / new_sp
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(src), str(dst))
                    new_sp_result = new_sp
                except OSError as e:
                    if is_quick_shot_pending:
                        print(f"⚠️ {vid}：腳本搬移失敗（quick-shot 豁免，繼續上線）：{e}")
                    else:
                        return False, f"{vid}：腳本搬移失敗 {sp} → {new_sp}（{e}）"
            elif dst.exists():
                new_sp_result = new_sp
            else:
                if is_quick_shot_pending:
                    print(f"⚠️ {vid}：腳本不存在（quick-shot 豁免，腳本待補）")
                else:
                    return False, f"{vid}：腳本檔案不存在（來源 {sp} 和目標 {new_sp} 都找不到）"

    video["status"] = new_status
    td = today_str()
    if "status_history" not in video:
        video["status_history"] = []
    video["status_history"].append({"status": new_status, "date": td})

    if new_sp_result is not None:
        video["script_path"] = new_sp_result

    if new_status == "已上線":
        if not video.get("publish_date"):
            video["publish_date"] = td
        pub = video.get("publish_date") or td
        try:
            pub_dt = datetime.strptime(pub, "%Y-%m-%d")
            from datetime import timedelta as _td
            video["backfill_due_date"] = (pub_dt + _td(days=_get_backfill_due_days(data))).strftime("%Y-%m-%d")
        except ValueError:
            video["backfill_due_date"] = None

    # video dict 是 items 中的同一引用，不需要額外賦值
    save_tracking(data, tracking_json=tracking_json)
    return True, f"{vid}：{current} → {new_status}"


def update_publish_date(data, vid, new_date, tracking_json=None):
    """更新上片日並自動重命名腳本檔案。
    回傳 (success, message, renamed_from, renamed_to)。"""
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}", None, None

    old_date = video.get("publish_date", "")
    if new_date == old_date:
        return False, f"{vid}：publish_date 已經是 {new_date}", None, None

    try:
        datetime.strptime(new_date, "%Y-%m-%d")
    except ValueError:
        return False, f"日期無效：{new_date}（應為合法的 YYYY-MM-DD）", None, None

    video["publish_date"] = new_date

    try:
        from datetime import timedelta as _td
        new_pub_dt = datetime.strptime(new_date, "%Y-%m-%d")
        video["backfill_due_date"] = (new_pub_dt + _td(days=_get_backfill_due_days(data))).strftime("%Y-%m-%d")
    except ValueError:
        pass

    sp = video.get("script_path") or ""
    renamed_from = None
    renamed_to = None
    if sp and "/" in sp:
        filename = sp.rsplit("/", 1)[1]
        dirname = sp.rsplit("/", 1)[0]
        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})_(.+)$", filename)
        if date_match:
            rest = date_match.group(2)
            new_filename = f"{new_date}_{rest}"
            new_sp = f"{dirname}/{new_filename}"

            if new_sp != sp:
                src = PROJECT_ROOT / sp
                dst = PROJECT_ROOT / new_sp
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                    renamed_from = sp
                    renamed_to = new_sp
                    video["script_path"] = new_sp
                elif dst.exists():
                    renamed_from = sp
                    renamed_to = new_sp
                    video["script_path"] = new_sp
                else:
                    print(f"⚠️ {vid}：腳本 {sp} 不存在，跳過搬移（僅更新路徑）")
                    renamed_from = sp
                    renamed_to = new_sp
                    video["script_path"] = new_sp

    save_tracking(data, tracking_json=tracking_json)

    if renamed_from:
        return True, f"{vid}：publish_date {old_date} → {new_date}，腳本已重命名", renamed_from, renamed_to
    else:
        return True, f"{vid}：publish_date {old_date} → {new_date}", None, None


def renumber_videos(data, vid_prefix=None, tracking_json=None, dry_run=False):
    """依 publish_date 排序後重新編號所有 VID。
    Phase 1: pre-check；Phase 2: execute（依靠 storage 原子寫入）。"""
    prefix = vid_prefix or _cfg.get_operator_paths().get("vid_prefix", "VID")
    videos = [item for item in data.get("items", []) if item.get("vid")]
    if not videos:
        return {}

    def _sort_key(v):
        pd = v.get("publish_date") or ""
        cd = v.get("created_date") or ""
        return (0 if pd else 1, pd, cd)

    sorted_videos = sorted(videos, key=_sort_key)

    vid_map = {}
    for i, v in enumerate(sorted_videos, 1):
        new_vid = f"{prefix}-{i:03d}"
        old_vid = v["vid"]
        if old_vid != new_vid:
            vid_map[old_vid] = new_vid

    if not vid_map:
        return {}

    # ── Phase 1: pre-check ──
    md_files_to_update = []
    preflight_errors = []
    for pattern in ("03-production-line/02-ready-to-shoot/**/*.md",
                     "03-production-line/03-done/**/*.md"):
        for filepath in glob.glob(str(PROJECT_ROOT / pattern), recursive=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = content
                for old_vid, new_vid in vid_map.items():
                    placeholder = f"__RENUMBER_{new_vid}__"
                    new_content = new_content.replace(
                        f"影片碼：{old_vid}", f"影片碼：{placeholder}"
                    )
                for nv in vid_map.values():
                    placeholder = f"__RENUMBER_{nv}__"
                    new_content = new_content.replace(placeholder, nv)
                if new_content != content:
                    if not os.access(filepath, os.W_OK):
                        preflight_errors.append(f"{filepath}：無寫入權限")
                    else:
                        md_files_to_update.append((filepath, content, new_content))
            except (OSError, UnicodeDecodeError) as e:
                preflight_errors.append(f"{filepath}：{e}")

    if preflight_errors:
        raise RuntimeError(
            f"renumber 前置驗證失敗（{len(preflight_errors)} 個問題），未做任何變更：\n  "
            + "\n  ".join(preflight_errors)
        )

    if dry_run:
        return vid_map

    # ── Phase 2: execute ──
    pp_path = _cfg.PERFORMANCE_PATTERNS_JSON
    try:
        for v in sorted_videos:
            old_vid = v["vid"]
            if old_vid in vid_map:
                v["vid"] = vid_map[old_vid]
            diag = (v.get("backfill") or {}).get("diagnosis")
            if diag and "prescriptions" in diag:
                updated_rx = []
                for rx in diag["prescriptions"]:
                    for ov, nv in vid_map.items():
                        rx = rx.replace(ov, f"__RENUM_{nv}__")
                    for nv in vid_map.values():
                        rx = rx.replace(f"__RENUM_{nv}__", nv)
                    updated_rx.append(rx)
                diag["prescriptions"] = updated_rx

        pipeline_data = data.get("_pipeline_ref", data)
        pipeline_data.setdefault("_meta", {})["next_vid"] = len(sorted_videos) + 1
        save_tracking(data, tracking_json=tracking_json)

        # 更新 performance-patterns.json（若存在）
        if pp_path.exists():
            with open(pp_path, "r", encoding="utf-8") as f:
                pp = json.load(f)
            for section in ("proven_openings", "proven_ctas", "proven_formulas", "risk_patterns"):
                for item in pp.get(section, []):
                    if "vid_evidence" in item:
                        item["vid_evidence"] = [
                            vid_map.get(v, v) for v in item["vid_evidence"]
                        ]
                    if "vid" in item and item["vid"] in vid_map:
                        item["vid"] = vid_map[item["vid"]]
            save_json(pp_path, pp, update_meta=False)

        # 更新腳本 .md 檔案
        for filepath, _original, new_content in md_files_to_update:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
    except Exception as e:
        raise RuntimeError(f"renumber 執行失敗：{e}")

    return vid_map


def save_script(data, vid, script_path, title_type, hook_type, version,
                verifier_prediction, generation_trace=None, tracking_json=None, skill_used=None):
    """腳本存檔：記錄偏好 + verifier 預測 + 生成追蹤到 pipeline.json。

    在 Kai 說「存檔」時由 Claude 呼叫。所有參數皆必填（quick-shot 豁免）。
    generation_trace (dict, optional): Skill 生成過程的關鍵信號，如：
      - patterns_injected: list[str] — 注入的 proven patterns
      - risk_patterns_avoided: list[str] — 迴避的 risk patterns
      - degradation_used: str | None — 觸發的降級路徑
      - persona_deviation_score: int | None — 偏離度分數
    回傳 (success, message)。
    """
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"

    if video.get("status") != "待拍":
        return False, f"{vid} 狀態為 {video['status']}，save 只能在「待拍」階段執行"

    # 從 _meta 讀取合法值
    meta = data.get("_meta", {})
    valid_tt = meta.get("valid_title_types", [])
    valid_ht = meta.get("valid_hook_types", [])
    valid_ver = meta.get("valid_versions", [])
    valid_vp = meta.get("valid_verifier_predictions", [])

    errors = []
    if valid_tt and title_type not in valid_tt:
        errors.append(f"title_type={title_type}（合法值：{', '.join(valid_tt)}）")
    if valid_ht and hook_type not in valid_ht:
        errors.append(f"hook_type={hook_type}（合法值：{', '.join(valid_ht)}）")
    if valid_ver and version not in valid_ver:
        errors.append(f"version={version}（合法值：{', '.join(valid_ver)}）")
    if valid_vp and verifier_prediction not in valid_vp:
        errors.append(f"verifier_prediction={verifier_prediction}（合法值：{', '.join(valid_vp)}）")
    if errors:
        return False, f"參數值無效：{'; '.join(errors)}"

    video["script_path"] = script_path
    video["title_type"] = title_type
    video["hook_type"] = hook_type
    video["version"] = version
    video["verifier_prediction"] = verifier_prediction
    video["save_date"] = today_str()
    if skill_used:
        video["skill_used"] = skill_used

    if generation_trace is not None:
        ok, msg, _warnings, normalized = validate_generation_trace(generation_trace, meta=meta)
        if not ok:
            return False, f"generation_trace 驗證失敗：{msg}"
        video["generation_trace"] = normalized

    data["videos"][idx] = video
    save_tracking(data, tracking_json=tracking_json)
    return True, f"{vid} 已存檔（版本={version} 標題={title_type} hook={hook_type} 預測={verifier_prediction}）"


def bind_script_path(data, vid, script_path, force=False, tracking_json=None):
    """僅綁定 script_path，不修改其他欄位。"""
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"

    sp = (script_path or "").strip()
    if not sp:
        return False, "script_path 不可為空"

    abs_path = PROJECT_ROOT / sp
    if not abs_path.exists():
        return False, f"腳本檔案不存在：{sp}"

    current = (video.get("script_path") or "").strip()
    if current and not force:
        return False, f"{vid} 已有 script_path={current}（如需覆寫請加 --force）"

    video["script_path"] = sp
    data["videos"][idx] = video
    save_tracking(data, tracking_json=tracking_json)
    if current and force:
        return True, f"{vid} script_path 已覆寫：{current} → {sp}"
    return True, f"{vid} script_path 已綁定：{sp}"


def delete_video(data, vid, tracking_json=None):
    """刪除指定 VID（僅刪資料，不動磁碟檔案）。"""
    _idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}", None

    pipeline_data = data.get("_pipeline_ref", data)
    items = pipeline_data.get("items", [])
    removed = None
    for i, item in enumerate(items):
        if item.get("vid") == vid:
            removed = items.pop(i)
            break
    if removed is None:
        return False, f"找不到 {vid}", None

    if "videos" in data:
        data["videos"] = [v for v in data["videos"] if v.get("vid") != vid]

    save_tracking(data, tracking_json=tracking_json)
    return True, f"{vid} 已刪除", removed


def record_verifier_scores(data, vid, scores, tracking_json=None):
    """記錄 script-verifier 的細項分數到 pipeline.json。

    scores 為 dict，預期鍵：
      conflict_score (int 0-10), retention_prediction (str),
      ai_residue_count (int), data_consistency (bool),
      format_complete (bool), pass_count (str like "5/5")
    回傳 (success, message)。
    """
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"

    ok, normalized_or_msg = validate_verifier_scores(scores)
    if not ok:
        return False, normalized_or_msg
    normalized = normalized_or_msg

    entry = {
        "conflict_score": normalized["conflict_score"],
        "retention_prediction": normalized["retention_prediction"],
        "ai_residue_count": normalized["ai_residue_count"],
        "data_consistency": normalized["data_consistency"],
        "format_complete": normalized["format_complete"],
        "pass_count": normalized["pass_count"],
        "date": today_str(),
    }
    video["verifier_scores"] = entry
    save_tracking(data, tracking_json=tracking_json)
    return True, f"{vid} verifier_scores 已記錄（{entry['pass_count']}）"


def validate_verifier_scores(scores):
    """驗證 verifier_scores payload，回傳 (success, normalized_dict_or_msg)。"""
    if not isinstance(scores, dict):
        return False, "verifier_scores 必須為物件（dict）"
    required_fields = [
        "conflict_score",
        "retention_prediction",
        "ai_residue_count",
        "data_consistency",
        "format_complete",
        "pass_count",
    ]
    unexpected = sorted(k for k in scores.keys() if k not in set(required_fields))
    if unexpected:
        return False, f"不支援的欄位：{', '.join(unexpected)}"
    missing = [k for k in required_fields if k not in scores]
    if missing:
        return False, f"缺少必要欄位：{', '.join(missing)}"

    conflict_score = scores.get("conflict_score")
    retention_prediction = scores.get("retention_prediction")
    ai_residue_count = scores.get("ai_residue_count")
    data_consistency = scores.get("data_consistency")
    format_complete = scores.get("format_complete")
    pass_count = scores.get("pass_count")

    if not isinstance(conflict_score, int) or isinstance(conflict_score, bool):
        return False, "conflict_score 必須為整數（0~10）"
    if conflict_score < 0 or conflict_score > 10:
        return False, "conflict_score 必須介於 0~10"
    if not isinstance(retention_prediction, str) or not retention_prediction.strip():
        return False, "retention_prediction 不可為空"
    if not isinstance(ai_residue_count, int) or isinstance(ai_residue_count, bool):
        return False, "ai_residue_count 必須為整數（>=0）"
    if ai_residue_count < 0:
        return False, "ai_residue_count 必須 >= 0"
    if not isinstance(data_consistency, bool):
        return False, "data_consistency 必須為 true/false"
    if not isinstance(format_complete, bool):
        return False, "format_complete 必須為 true/false"
    if not isinstance(pass_count, str) or not re.match(r"^\d+/5$", pass_count.strip()):
        return False, 'pass_count 格式必須為 "N/5"'
    pass_count_num = int(pass_count.strip().split("/")[0])
    if pass_count_num < 0 or pass_count_num > 5:
        return False, 'pass_count 分子必須介於 0~5（格式 "N/5"）'

    return True, {
        "conflict_score": conflict_score,
        "retention_prediction": retention_prediction.strip(),
        "ai_residue_count": ai_residue_count,
        "data_consistency": data_consistency,
        "format_complete": format_complete,
        "pass_count": pass_count.strip(),
    }


def add_transcript(data, vid, transcript_text, tracking_json=None):
    """為已上線影片補錄口播逐字稿。回傳 (success, message)。"""
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"
    if video.get("status") != "已上線":
        return False, f"{vid} 狀態為 {video['status']}，只有「已上線」可補逐字稿"
    if not transcript_text or not transcript_text.strip():
        return False, "逐字稿內容不可為空"

    video["transcript"] = transcript_text.strip()
    was_pending = video.get("script_status") == "待補"
    if was_pending:
        video["script_status"] = None
    save_tracking(data, tracking_json=tracking_json)
    char_count = len(video["transcript"])
    cleared_msg = "，script_status 已從「待補」清除" if was_pending else ""
    return True, f"{vid} 逐字稿已儲存（{char_count} 字{cleared_msg}）"


def query_pending_scripts(data):
    """查詢所有 script_status=待補 的影片，按建檔日排序。"""
    pending = []
    td = today_str()
    videos = data.get("videos", [item for item in data.get("items", []) if item.get("vid")])
    for v in videos:
        if v.get("script_status") == "待補":
            created = v.get("created_date") or ""
            days = 0
            if created:
                try:
                    days = (datetime.strptime(td, "%Y-%m-%d")
                            - datetime.strptime(created, "%Y-%m-%d")).days
                except ValueError:
                    pass
            pending.append({
                "vid": v["vid"],
                "topic": v.get("topic", ""),
                "status": v.get("status", ""),
                "created_date": created,
                "days_pending": days,
                "has_transcript": bool(v.get("transcript")),
            })
    pending.sort(key=lambda x: -x["days_pending"])
    return pending


def format_video(v):
    """單支影片的格式化輸出。"""
    tag_val = v.get("tags", v.get("tag", ""))
    parts = [
        f"  影片碼：{v['vid']}",
        f"  主題：{v['topic']}",
        f"  標籤：{tag_val}",
        f"  狀態：{v['status']}",
        f"  建檔日：{v.get('created_date', '?')}",
    ]
    if v.get("publish_date"):
        parts.append(f"  上片日：{v['publish_date']}")
    if v.get("script_path"):
        parts.append(f"  腳本：{v['script_path']}")
    if v.get("title"):
        parts.append(f"  封面標題：{v['title']}")
    if v.get("skill_used"):
        parts.append(f"  Skill：{v['skill_used']}")
    if v.get("source") and v["source"] != "pipeline":
        parts.append(f"  來源：{v['source']}")
    if v.get("script_status"):
        parts.append(f"  腳本狀態：{v['script_status']}")
    if v.get("source_idea_id"):
        parts.append(f"  來源靈感：{v['source_idea_id']}")
    if v.get("backfill_due_date") and not v.get("backfill"):
        parts.append(f"  回填截止：{v['backfill_due_date']}")
    if v.get("notes"):
        parts.append(f"  備註：{v['notes']}")
    if v.get("backfill"):
        bf = v["backfill"]
        parts.append(f"  回填：觀看{bf.get('views',0)} | 3秒{bf.get('retention_3s','?')}% | 完播{bf.get('completion_rate','?')}%")
    if v.get("transcript"):
        preview = v["transcript"][:60].replace("\n", " ")
        parts.append(f"  逐字稿：{preview}...（{len(v['transcript'])}字）")
    return "\n".join(parts)
