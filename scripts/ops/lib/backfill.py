#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回填管線：表現分類 + 資料回填 + 學習提取。

拆分後的模組結構：
- patterns.py:       PATTERN_KEYS + pattern CRUD + decay + cleanup
- diagnosis.py:      diagnose_video + _classify_post_type
- auto_extract.py:   腳本解析 + auto_extract_from_script
- backfill_report.py: performance_report + query_unextracted
- backfill.py (本檔): classify + backfill_video + extract_learning + 公開 API re-export
"""

from .config import (
    PERFORMANCE_THRESHOLDS, PERFORMANCE_DISPLAY, today_str,
)
from .pipeline import find_video, save_tracking

# ── 子模組 re-export（維持所有消費者的 import 不變）────────
from .patterns import (  # noqa: F401
    PATTERN_KEYS, win_rate_note,
    load_performance_patterns, save_performance_patterns,
    _check_pattern_decay, _add_vid_evidence,
    _remove_vid_from_patterns, _remove_vid_from_low_evidence,
    cleanup_unverified_formulas, compute_pattern_stats,
    cross_dimensional_stats,
)
from .diagnosis import diagnose_video, _classify_post_type  # noqa: F401
from .auto_extract import (  # noqa: F401
    _parse_script_body, _lite_g3_check,
    _OPENING_PATTERNS, _CTA_PATTERNS, _TURNING_WORDS, _G3_HOOK_SIGNALS,
    _best_match, auto_extract_from_script,
)
from .backfill_report import performance_report, query_unextracted  # noqa: F401


# ── 表現分類 ─────────────────────────────────────────────

def resolve_performance_thresholds(meta=None):
    """從 pipeline _meta.thresholds.performance 解析 ops 格式門檻；缺漏 / 格式不符 fallback 常數。

    _meta 是門檻 SSoT（data/*/pipeline/_meta.json）。讓存檔分類能跟著 _meta 走、不寫死。
    display helper（無 data context）仍用 PERFORMANCE_THRESHOLDS 常數、該常數已硬性要求與
    _meta 一致（見 config.py 註解 + test_classify_performance_display_ssot）。
    """
    perf = ((meta or {}).get("thresholds") or {}).get("performance")
    if not isinstance(perf, dict):
        return PERFORMANCE_THRESHOLDS
    try:
        ha, hb, lo = perf["high_A"], perf["high_B"], perf["low"]
        return {
            "high": {
                "path_A": {
                    "retention_3s_min": ha["retention_3s"],
                    "completion_rate_min": ha["completion_rate"],
                },
                "path_B": {
                    "views_min": hb["views"],
                    "completion_rate_min": hb["completion_rate"],
                },
            },
            "low": {
                "retention_3s_max": lo["retention_3s_below"],
                "completion_rate_max": lo["completion_rate_below"],
            },
        }
    except (KeyError, TypeError):
        return PERFORMANCE_THRESHOLDS


def classify_performance(views, retention_3s, completion_rate, meta=None):
    """根據門檻自動分類表現等級，回傳 (level, path, reason)。

    meta=None 時用 PERFORMANCE_THRESHOLDS 常數（display helper 等無 data context 路徑）；
    存檔 / 驗證 / 遷移路徑傳 pipeline _meta、門檻跟著 SSoT 走（Bounded：只存檔相關路徑讀 _meta）。
    """
    th = resolve_performance_thresholds(meta)
    ha = th["high"]["path_A"]
    hb = th["high"]["path_B"]
    # L-0024 hardened：retention/completion 為 None 代表「來源無資料」、需 fall through 不可參與比較。
    # 兩條 high 路徑：A 需 retention+completion、B 只需 views+completion。
    # completion 缺 → 兩路徑都判不了 → unknown
    if completion_rate is None:
        return "unknown", None, "completion 資料不完整、無法判定（L-0024）"
    # completion 有：先試 high_B（不需 retention）
    high_b = views >= hb["views_min"] and \
             completion_rate >= hb["completion_rate_min"]
    if retention_3s is None:
        # 沒 retention：只能判 high_B；若不過、無法區分 normal/low、歸 unknown
        if high_b:
            return "high", "B", (
                f"觀看{views:,}≥{hb['views_min']:,}"
                f" + 完播{completion_rate}%≥{hb['completion_rate_min']}%（retention 不完整）"
            )
        return "unknown", None, "retention 不完整、views 未達 high_B 門檻、無法區分 normal/low（L-0024）"
    high_a = retention_3s >= ha["retention_3s_min"] and \
             completion_rate >= ha["completion_rate_min"]

    if high_a and high_b:
        return "high", "AB", (
            f"留存{retention_3s}%≥{ha['retention_3s_min']}%"
            f" + 完播{completion_rate}%≥{ha['completion_rate_min']}%"
            f" + 觀看{views:,}≥{hb['views_min']:,}"
        )
    elif high_a:
        return "high", "A", (
            f"留存{retention_3s}%≥{ha['retention_3s_min']}%"
            f" + 完播{completion_rate}%≥{ha['completion_rate_min']}%"
        )
    elif high_b:
        return "high", "B", (
            f"觀看{views:,}≥{hb['views_min']:,}"
            f" + 完播{completion_rate}%≥{hb['completion_rate_min']}%"
        )

    lo = th["low"]
    low_retention = retention_3s < lo["retention_3s_max"]
    low_completion = completion_rate < lo["completion_rate_max"]
    if low_retention or low_completion:
        reasons = []
        if low_retention:
            reasons.append(f"留存{retention_3s}%<{lo['retention_3s_max']}%")
        if low_completion:
            reasons.append(f"完播{completion_rate}%<{lo['completion_rate_max']}%")
        return "low", None, " + ".join(reasons)

    return "normal", None, f"留存{retention_3s}% 完播{completion_rate}%（未達高/低門檻）"


def classify_performance_display(views=0, retention_3s=0, completion_rate=0):
    """回傳帶 emoji 的顯示用等級（給 Sheets 用）。紅綠燈：觀看低的高留存不算真正高表現。"""
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
    level, path, _reason = classify_performance(v, r, c)
    if level == "high" and path in ("B", "AB"):
        return PERFORMANCE_DISPLAY.get("high_reach", "🟢 高")
    elif level == "high":
        return PERFORMANCE_DISPLAY.get("high_retention", "🟡 留存高")
    return PERFORMANCE_DISPLAY.get(level, "🟡 普通")


# ── 回填 ─────────────────────────────────────────────────

def _try_auto_learning(data, vid, video, level, diagnosis, pdata=None):
    """回填後自動提取學習記錄（高/低表現 + 有腳本時）。

    高表現：auto_extract_from_script 猜測 opening/cta → extract_learning
    低表現：從 diagnosis weaknesses 推導 failure_mode → extract_learning
    普通表現：標記 learning_extracted=True，跳過提取

    回傳 dict 描述結果，或 None（已提取過 / 不適用）。
    """
    bf = video.get("backfill") or {}
    if bf.get("learning_extracted"):
        return None  # 已提取過

    if level == "normal":
        # 普通表現：數據已記錄、診斷已完成，標記為已提取
        bf["learning_extracted"] = True
        return {"action": "mark_normal", "msg": f"{vid} 普通表現，標記已提取（無需額外動作）"}

    sp = video.get("script_path") or ""
    transcript = video.get("transcript")

    if level == "high":
        # 嘗試從腳本自動解析
        parsed = None
        if sp or transcript:
            parsed = auto_extract_from_script(sp, transcript=transcript)

        if parsed and (parsed.get("opening_guess") or parsed.get("cta_guess")):
            ok, msg = extract_learning(
                data, vid,
                opening=parsed.get("opening_guess"),
                cta=parsed.get("cta_guess"),
                hook=parsed.get("hook", "")[:80],
                persist=False,
                pdata=pdata,
            )
            if ok:
                result = {"action": "auto_high", "msg": msg}
                result["patterns_changed"] = True
                if parsed.get("opening_guess"):
                    result["opening"] = parsed["opening_guess"]
                if parsed.get("cta_guess"):
                    result["cta"] = parsed["cta_guess"]
                missing = []
                if not parsed.get("opening_guess"):
                    missing.append("opening")
                if not parsed.get("cta_guess"):
                    missing.append("CTA")
                if missing:
                    result["partial"] = f"（{' + '.join(missing)} 未自動解析，建議手動補齊）"
                return result
        # 無法自動解析 → 不強制，留給手動
        return {"action": "need_manual_high",
                "msg": f"{vid} 高表現但無法自動解析（腳本：{sp or '無'}），請手動 extract-learning"}

    if level == "low":
        # 從 diagnosis weaknesses 推導 failure_mode
        weaknesses = diagnosis.get("weaknesses", [])
        if weaknesses:
            failure_mode = weaknesses[0].split("（")[0]  # e.g. "Hook 弱"
            failure_detail = "; ".join(weaknesses)
        else:
            failure_mode = "表現低於門檻"
            failure_detail = "留存或完播未達標"

        # 嘗試從腳本解析 opening/cta 以觸發 pattern decay
        parsed = None
        if sp or transcript:
            parsed = auto_extract_from_script(sp, transcript=transcript)

        ok, msg = extract_learning(
            data, vid,
            failure_mode=failure_mode,
            failure_detail=failure_detail,
            opening=parsed.get("opening_guess") if parsed else None,
            cta=parsed.get("cta_guess") if parsed else None,
            persist=False,
            pdata=pdata,
        )
        if ok:
            return {
                "action": "auto_low",
                "failure_mode": failure_mode,
                "msg": msg,
                "patterns_changed": True,
            }
        return {"action": "need_manual_low",
                "msg": f"{vid} 低表現自動提取失敗：{msg}"}

    return None


def backfill_video(data, vid, views, retention_3s, completion_rate,
                   engagement_rate=None, profile_clicks=None,
                   likes=None, comments=None, shares=None, saves=None,
                   reposts=None, new_followers=None, reached_accounts=None,
                   video_length_seconds=None, avg_watch_seconds=None,
                   profile_source_pct=None):
    """寫入回填數據 + 自動分類表現。"""
    # 邊界驗證：核心數值必須在合理範圍內
    bounds_errors = []
    if views < 0:
        bounds_errors.append(f"views={views}（應 ≥ 0）")
    if not (0 <= retention_3s <= 100):
        bounds_errors.append(f"retention_3s={retention_3s}（應 0~100）")
    if not (0 <= completion_rate <= 100):
        bounds_errors.append(f"completion_rate={completion_rate}（應 0~100）")
    # L-0024：retention_3s=0.0 為來源缺漏 sentinel（非真值），views>0 時禁止寫入。
    if views > 0 and retention_3s == 0:
        bounds_errors.append(
            "retention_3s=0 與 views>0 的組合無效（L-0024 sentinel）；"
            "請改填 null 流程或先修正來源資料"
        )
    if engagement_rate is not None and not (0 <= engagement_rate <= 100):
        bounds_errors.append(f"engagement_rate={engagement_rate}（應 0~100）")
    if profile_clicks is not None and profile_clicks < 0:
        bounds_errors.append(f"profile_clicks={profile_clicks}（應 ≥ 0）")
    for name, val in [("likes", likes), ("comments", comments), ("shares", shares),
                      ("saves", saves), ("reposts", reposts),
                      ("new_followers", new_followers), ("reached_accounts", reached_accounts)]:
        if val is not None and val < 0:
            bounds_errors.append(f"{name}={val}（應 ≥ 0）")
    if video_length_seconds is not None and video_length_seconds <= 0:
        bounds_errors.append(f"video_length_seconds={video_length_seconds}（應 > 0）")
    if avg_watch_seconds is not None and avg_watch_seconds < 0:
        bounds_errors.append(f"avg_watch_seconds={avg_watch_seconds}（應 ≥ 0）")
    if profile_source_pct is not None and not (0 <= profile_source_pct <= 100):
        bounds_errors.append(f"profile_source_pct={profile_source_pct}（應 0~100）")
    if bounds_errors:
        return False, f"數值超出合理範圍：{'; '.join(bounds_errors)}", None

    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}", None
    if video.get("status") != "已上線":
        return False, f"{vid} 狀態為 {video['status']}，只有「已上線」可回填", None

    sp = video.get("script_path") or ""
    ss = video.get("script_status")
    backfill_warnings = []
    if (avg_watch_seconds is not None and video_length_seconds is not None
            and avg_watch_seconds > video_length_seconds):
        backfill_warnings.append(
            f"avg_watch_seconds({avg_watch_seconds})>"
            f"video_length_seconds({video_length_seconds})，完播率可能不準確"
        )
    if not sp:
        backfill_warnings.append(f"{vid} 缺腳本路徑（script_path=null）")
    elif ss == "待補":
        backfill_warnings.append(f"{vid} 腳本待補（quick-shot 尚未提供腳本）")

    level, path, reason = classify_performance(
        views, retention_3s, completion_rate, meta=data.get("_meta")
    )

    bf = {
        "backfilled_date": today_str(),
        "views": views,
        "retention_3s": retention_3s,
        "completion_rate": completion_rate,
        "performance": level,
        "learning_extracted": False,
    }
    if path:
        bf["path"] = path
    optional = {
        "engagement_rate": engagement_rate, "profile_clicks": profile_clicks,
        "likes": likes, "comments": comments, "shares": shares, "saves": saves,
        "reposts": reposts, "new_followers": new_followers,
        "reached_accounts": reached_accounts,
        "video_length_seconds": video_length_seconds,
        "avg_watch_seconds": avg_watch_seconds,
        "profile_source_pct": profile_source_pct,
    }
    for k, v in optional.items():
        if v is not None:
            bf[k] = v

    # 保留既有欄位（如 reels_tab_pct 等非標準欄位），再覆蓋新值
    existing_bf = video.get("backfill") or {}
    old_level = existing_bf.get("performance")

    # re-backfill 級別變更偵測
    if old_level == "high" and level != "high" and existing_bf.get("learning_extracted"):
        # 降級：高表現 → 非高表現，清除舊 learning + patterns 幽靈證據
        old_learning = video.get("learning") or {}
        _remove_vid_from_patterns(vid, old_learning)
        video.pop("learning", None)
        backfill_warnings.append(
            f"re-backfill 降級（{old_level}→{level}），已清除舊 learning 記錄"
            f" + performance-patterns 中 {vid} 的證據"
        )
        # 不保留舊的 learning_extracted
    elif old_level == "low" and level != "low" and existing_bf.get("learning_extracted"):
        # 升級：低表現 → 非低表現，清除 low_evidence + risk_patterns 幽靈衰減
        cleaned = _remove_vid_from_low_evidence(vid)
        video.pop("learning", None)
        if cleaned:
            backfill_warnings.append(
                f"re-backfill 升級（{old_level}→{level}），已清除 low_evidence"
                f" + risk_patterns 中 {vid} 的記錄"
            )
        # 不保留舊的 learning_extracted
    elif existing_bf.get("learning_extracted"):
        bf["learning_extracted"] = True

    merged = {**existing_bf, **bf}

    # 自動診斷（回填 + 診斷一次性寫入，避免中間態）
    diag = diagnose_video(merged)
    merged["diagnosis"] = diag

    video["backfill"] = merged
    data["videos"][idx] = video

    result = {
        "vid": vid, "level": level, "path": path, "reason": reason,
        "views": views, "retention_3s": retention_3s,
        "completion_rate": completion_rate,
        "warnings": backfill_warnings,
        "diagnosis": diag,
    }

    # Quick-shot 輕量 G3 分析（回填後自動觸發）
    if video.get("source") == "quick-shot" and sp and sp != "系統前上線":
        g3 = _lite_g3_check(sp)
        if g3:
            result["lite_g3"] = g3

    # 自動學習提取 + 統計重算共用同一份 in-memory pattern data。
    # （修既有 bug：原本 auto-learning 改 pattern_data、卻在另一份 freshly-load 的 pdata 上
    #   算 stats 並先存，最後再存 pattern_data 覆蓋掉 → 含新 pattern 但 win_rate/confidence
    #   是上一輪的舊值。統一成一份、算完一次存，避免 stats 落後一個回填週期。）
    pattern_data = load_performance_patterns()
    auto_learn = _try_auto_learning(data, vid, video, level, diag, pdata=pattern_data)
    if auto_learn:
        result["auto_learning"] = auto_learn
        action = auto_learn.get("action", "")
        if action.startswith("need_manual"):
            result["warnings"].append(auto_learn["msg"])
        if auto_learn.get("partial"):
            result["warnings"].append(auto_learn["partial"])

    # 每次回填後在「含本輪新學習 pattern 的同一份」上重算統計（win_rate/confidence）
    stats_updated = compute_pattern_stats(pattern_data, data.get("items", data.get("videos", [])))
    if stats_updated or (auto_learn and auto_learn.get("patterns_changed")):
        save_performance_patterns(pattern_data)

    data["videos"][idx] = video
    save_tracking(data)

    return True, f"{vid} 回填完成：{level}（{reason}）", result


# ── 學習提取 ─────────────────────────────────────────────

def extract_learning(data, vid, opening=None, hook=None, turning_point=None,
                     cta=None, formula=None, failure_mode=None, failure_detail=None,
                     persist=True, pdata=None):
    """提取高/低表現特徵，寫入 video-tracking + performance-patterns.json。"""
    idx, video = find_video(data, vid)
    if video is None:
        return False, f"找不到 {vid}"

    bf = video.get("backfill")
    if not bf:
        return False, f"{vid} 尚未回填數據，請先執行 backfill"

    level = bf.get("performance", "normal")
    pdata = pdata if pdata is not None else load_performance_patterns()
    patterns_changed = False

    if level == "high":
        if not opening and not cta:
            return False, "高表現提取至少需要 --opening 或 --cta 其一"

        learning = {"extracted_date": today_str(), "type": "high"}
        if opening:
            learning["opening"] = opening
        if hook:
            learning["hook"] = hook
        if turning_point:
            learning["turning_point"] = turning_point
        if cta:
            learning["cta"] = cta
        if formula:
            learning["formula"] = formula

        video["learning"] = learning
        bf["learning_extracted"] = True
        video["backfill"] = bf

        updated = []
        if opening:
            _add_vid_evidence(pdata, "proven_openings", opening, vid)
            updated.append(f"opening {opening}")
        if cta:
            _add_vid_evidence(pdata, "proven_ctas", cta, vid)
            updated.append(f"CTA {cta}")
        if formula:
            _add_vid_evidence(pdata, "proven_formulas", formula, vid)
            updated.append(f"formula {formula}")
        patterns_changed = True

    elif level == "low":
        if not failure_mode:
            return False, "低表現提取需要 --failure-mode"
        learning = {
            "extracted_date": today_str(), "type": "low",
            "failure_mode": failure_mode,
            "failure_detail": failure_detail or "",
        }
        if opening:
            learning["opening"] = opening
        if cta:
            learning["cta"] = cta
        video["learning"] = learning
        bf["learning_extracted"] = True
        video["backfill"] = bf

        risks = pdata.setdefault("risk_patterns", [])
        existing = next((r for r in risks if r.get("vid") == vid), None)
        if existing:
            existing["mode"] = failure_mode
            existing["detail"] = failure_detail or ""
            existing["date"] = today_str()
        else:
            risks.append({
                "mode": failure_mode, "detail": failure_detail or "",
                "vid": vid, "date": today_str(),
            })

        # 自動衰減：低表現影片使用的 proven pattern 累計 low_evidence
        _check_pattern_decay(pdata, opening=opening, cta=cta, formula=formula, vid=vid)

        patterns_changed = True
        updated = [f"risk_pattern: {failure_mode}"]
        if opening:
            updated.append(f"decay_check: opening {opening}")
        if cta:
            updated.append(f"decay_check: cta {cta}")
        if formula:
            updated.append(f"decay_check: formula {formula}")

    else:
        # normal：若有手動傳入參數，記錄特徵（但不加 vid_evidence，不影響 patterns 統計）
        has_manual = opening or cta or hook or turning_point or formula
        learning = {"extracted_date": today_str(), "type": "normal"}
        if has_manual:
            if opening:
                learning["opening"] = opening
            if hook:
                learning["hook"] = hook
            if turning_point:
                learning["turning_point"] = turning_point
            if cta:
                learning["cta"] = cta
            if formula:
                learning["formula"] = formula
            learning["notes"] = "普通表現，手動記錄特徵（不影響 proven patterns）"
        else:
            learning["notes"] = "表現普通，無需提取特徵"
        video["learning"] = learning
        bf["learning_extracted"] = True
        video["backfill"] = bf
        updated = []
        if opening:
            updated.append(f"opening {opening}")
        if cta:
            updated.append(f"CTA {cta}")
        if not updated:
            updated = ["skip（normal）"]

    data["videos"][idx] = video
    if persist:
        save_tracking(data)
        if patterns_changed:
            save_performance_patterns(pdata)
    return True, f"{vid} 學習提取完成（{level}）：{', '.join(updated)}"
