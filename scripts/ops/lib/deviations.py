#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腳本 vs 實拍偏差記錄 + 分析。

回填後收集 Kai 的拍攝偏差，累積後分析哪些句型常被改動，
交叉比對表現數據，提議 banned-words 更新。
"""

import re
from difflib import SequenceMatcher

from .config import PROJECT_ROOT, today_str, current_operator
from .lessons import add_lesson, load_lessons, save_lessons
from .pipeline import load_pipeline, find_by_vid

# ── 路徑 ─────────────────────────────────────────────────

_EMPTY = {"description": "腳本 vs 實拍偏差記錄", "deviations": []}

VALID_LEVELS = {"minimal", "moderate", "significant"}


# ── 讀寫 ─────────────────────────────────────────────────

def load_deviations():
    entries = []
    for lesson in load_lessons(current_operator()):
        if lesson.get("origin") != "deviation":
            continue
        note = lesson.get("source_note") if isinstance(lesson.get("source_note"), dict) else {}
        entries.append(
            {
                "vid": note.get("vid") or lesson.get("pattern"),
                "date": note.get("date") or lesson.get("updated_at"),
                "level": note.get("level") or "minimal",
                "changes": note.get("changes") or [],
                "performance": note.get("performance"),
            }
        )
    return {"description": _EMPTY["description"], "deviations": entries}


# ── 記錄偏差 ─────────────────────────────────────────────

def record_deviation(vid, level, changes=None):
    """記錄一支影片的拍攝偏差。

    Args:
        vid: 影片碼，如 VID-035
        level: minimal | moderate | significant
        changes: list of dict, 每個含 original / actual / reason（皆為可選）

    Returns:
        (ok: bool, msg: str)
    """
    if level not in VALID_LEVELS:
        return False, f"level 必須為 {', '.join(sorted(VALID_LEVELS))}，收到：{level}"

    if changes is not None:
        if not isinstance(changes, list):
            return False, "changes 必須為 list"
        for i, c in enumerate(changes):
            if not isinstance(c, dict):
                return False, f"changes[{i}] 必須為 dict"

    existing_idx = next((d for d in load_deviations().get("deviations", []) if d.get("vid") == vid), None)

    entry = {
        "vid": vid,
        "date": today_str(),
        "level": level,
        "changes": changes or [],
        "performance": None,  # 由 backfill_link 回填
    }
    add_lesson(
        operator=current_operator(),
        origin="deviation",
        pattern=vid,
        counter_pattern=None,
        evidence=[vid],
        scope=["script"],
        stage="soft",
        source_note=entry,
    )
    change_count = len(entry["changes"])
    action = "更新" if existing_idx else "新增"
    return True, f"{vid} 偏差{action}完成（{level}，{change_count} 個改動）"


def link_performance(vid, performance):
    """將回填的表現等級回寫到偏差記錄。

    在 backfill 後呼叫，將 high/normal/low 寫入對應的 deviation entry。
    """
    operator = current_operator()
    lessons = load_lessons(operator)
    for item in lessons:
        if item.get("origin") != "deviation" or item.get("pattern") != vid:
            continue
        note = item.get("source_note") if isinstance(item.get("source_note"), dict) else {"vid": vid}
        note["performance"] = performance
        item["source_note"] = note
        item["updated_at"] = today_str()
        save_lessons(operator, lessons)
        return True
    return False


# ── 計數 ─────────────────────────────────────────────────

def count_deviations():
    """回傳有效偏差記錄數（有 performance 的才算完成）。"""
    data = load_deviations()
    return sum(1 for d in data.get("deviations", []) if d.get("performance"))


# ── 分析 ─────────────────────────────────────────────────

def analyze_deviations():
    """分析累積的偏差記錄，回傳結構化報告。

    Returns:
        dict with keys:
        - total: 總記錄數
        - with_changes: 有改動的記錄數
        - level_dist: {minimal: N, moderate: N, significant: N}
        - perf_by_level: {minimal: {high: N, normal: N, low: N}, ...}
        - frequent_originals: [{original, count, performances}] 常被改的原文
        - frequent_reasons: [{reason, count}] 常見改動原因
        - trend: 最近 5 支 vs 之前的改動程度比較
    """
    data = load_deviations()
    devs = [d for d in data.get("deviations", []) if d.get("performance")]

    if not devs:
        return {"total": 0, "sufficient": False}

    total = len(devs)
    with_changes = sum(1 for d in devs if d.get("changes"))

    # 等級分佈
    level_dist = {"minimal": 0, "moderate": 0, "significant": 0}
    for d in devs:
        lv = d.get("level", "minimal")
        if lv in level_dist:
            level_dist[lv] += 1

    # 等級 × 表現交叉
    perf_by_level = {}
    for lv in VALID_LEVELS:
        perf_by_level[lv] = {"high": 0, "normal": 0, "low": 0}
    for d in devs:
        lv = d.get("level", "minimal")
        perf = d.get("performance", "normal")
        if lv in perf_by_level and perf in perf_by_level[lv]:
            perf_by_level[lv][perf] += 1

    # 統計常被改的原文
    original_stats = {}
    reason_stats = {}
    for d in devs:
        perf = d.get("performance", "normal")
        for c in d.get("changes", []):
            orig = c.get("original", "").strip()
            if orig:
                if orig not in original_stats:
                    original_stats[orig] = {"count": 0, "performances": []}
                original_stats[orig]["count"] += 1
                original_stats[orig]["performances"].append(perf)
            reason = c.get("reason", "").strip()
            if reason:
                reason_stats[reason] = reason_stats.get(reason, 0) + 1

    frequent_originals = sorted(
        [{"original": k, **v} for k, v in original_stats.items()],
        key=lambda x: x["count"], reverse=True,
    )

    frequent_reasons = sorted(
        [{"reason": k, "count": v} for k, v in reason_stats.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # 趨勢：最近 5 支 vs 之前
    level_score = {"minimal": 0, "moderate": 1, "significant": 2}
    if total >= 6:
        recent = devs[-5:]
        earlier = devs[:-5]
        recent_avg = sum(level_score.get(d.get("level", "minimal"), 0) for d in recent) / len(recent)
        earlier_avg = sum(level_score.get(d.get("level", "minimal"), 0) for d in earlier) / len(earlier)
        if recent_avg < earlier_avg - 0.3:
            trend = "improving"
        elif recent_avg > earlier_avg + 0.3:
            trend = "worsening"
        else:
            trend = "stable"
        trend_detail = {"recent_avg": round(recent_avg, 2), "earlier_avg": round(earlier_avg, 2)}
    else:
        trend = "insufficient"
        trend_detail = {}

    return {
        "total": total,
        "sufficient": total >= 10,
        "with_changes": with_changes,
        "level_dist": level_dist,
        "perf_by_level": perf_by_level,
        "frequent_originals": frequent_originals,
        "frequent_reasons": frequent_reasons,
        "trend": trend,
        "trend_detail": trend_detail,
    }


# ── 腳本文字提取 ────────────────────────────────────────────

# 段落標記 **開頭（0-3s）** / 【畫面】/ --- / > metadata / ## 標題
_SECTION_HEADER = re.compile(r"^\*\*.*\*\*$")
_STAGE_DIRECTION = re.compile(r"^【(?!字幕收尾).*】")
_DIALOGUE_LINE = re.compile(r"^(?![（(])(\S+?)(?:（.*?）)?：(.+)")
_PAREN_CUE = re.compile(r"^[（(].*[）)]$")
_QUOTED_LINE = re.compile(r"[「『](.+?)[」』]")
_TABLE_LINE = re.compile(r"^\|.*\|$")
_CHECKBOX = re.compile(r"^- \[[ x]\]")


def extract_spoken_lines(script_content):
    """從腳本內容提取純口說文字。

    支援兩種格式：
    1. 簡單格式：「...」引號內的對白
    2. 對話格式：角色名：對白

    Returns:
        list[str] — 每句一行的口說文字（已清除引號和角色名）
    """
    lines = script_content.splitlines()
    spoken = []

    # 跳過 metadata（--- 之前）
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            body_start = i + 1
            break

    # 掃描結構拆解/附錄/Gates 起始位置 → 截斷
    body_end = len(lines)
    for i in range(body_start, len(lines)):
        s = lines[i].strip()
        if s.startswith("## 結構拆解") or s.startswith("## 可複製公式") \
                or s.startswith("## Hard Gates") or s.startswith("## humanizer") or s.startswith("## quality"):
            body_end = i
            break

    in_dialogue = False  # 追蹤是否在多行對白中

    for line in lines[body_start:body_end]:
        s = line.strip()
        if not s:
            in_dialogue = False
            continue

        # 跳過非口說內容
        if s.startswith(">") or s.startswith("#") or s.startswith("---"):
            in_dialogue = False
            continue
        if _SECTION_HEADER.match(s):
            in_dialogue = False
            continue
        if _STAGE_DIRECTION.match(s):
            in_dialogue = False
            continue
        if _TABLE_LINE.match(s):
            in_dialogue = False
            continue
        if _CHECKBOX.match(s):
            in_dialogue = False
            continue
        if s.startswith("| ") or s.startswith("|--"):
            in_dialogue = False
            continue

        # 腳本資訊表格下的 key-value (## 腳本資訊 區塊)
        if s.startswith("## 腳本資訊"):
            in_dialogue = False
            continue

        # 跳過括號舞台指示，如（字卡：他都聽到了）
        if _PAREN_CUE.match(s):
            in_dialogue = False
            continue

        # 對話格式：Kai：xxx / 安：xxx
        dm = _DIALOGUE_LINE.match(s)
        if dm:
            spoken.append(dm.group(2).strip())
            in_dialogue = True
            continue

        # 多行對白的續行（前一行是對話格式，當前行是純文字）
        if in_dialogue and spoken:
            spoken[-1] += s
            continue

        # 「引號」格式
        quotes = _QUOTED_LINE.findall(s)
        if quotes:
            for q in quotes:
                spoken.append(q.strip())
            in_dialogue = False
            continue

        # 字幕收尾行 【字幕收尾】開店不只是算帳，是扛人
        if s.startswith("【字幕收尾】"):
            spoken.append(s[len("【字幕收尾】"):].strip())
            in_dialogue = False
            continue

        in_dialogue = False

    return spoken


# ── 智能比對 ──────────────────────────────────────────────

def _normalize(text):
    """正規化文字：移除標點差異、統一空白。"""
    # 移除常見中文標點（保留核心內容）
    for ch in "，。、！？；：「」『』（）—…～":
        text = text.replace(ch, "")
    return text.strip()


def _sentence_split(text):
    """將文字切成句子（依句號/換行/問號/驚嘆號）。"""
    # 先按換行切
    parts = text.strip().splitlines()
    sentences = []
    for part in parts:
        # 再按句末標點切
        subs = re.split(r"(?<=[。！？\n])", part.strip())
        for s in subs:
            s = s.strip()
            if s:
                sentences.append(s)
    return sentences


def diff_script(original_lines, subtitle_text):
    """比對原始腳本口說行 vs 實際字幕文字。

    Args:
        original_lines: list[str] — extract_spoken_lines 的結果
        subtitle_text: str — Kai 貼上的字幕全文

    Returns:
        dict:
        - similarity: float 0-1
        - level: minimal | moderate | significant
        - changes: list[dict] with original / actual / type
        - summary: str 人類可讀摘要
    """
    if not original_lines and not subtitle_text.strip():
        return {
            "similarity": 1.0,
            "level": "minimal",
            "changes": [],
            "summary": "兩邊皆為空",
        }

    # 準備比對文字
    orig_text = "\n".join(original_lines)
    sub_sentences = _sentence_split(subtitle_text)

    # 正規化後計算整體相似度
    norm_orig = _normalize(orig_text)
    norm_sub = _normalize("\n".join(sub_sentences))
    similarity = SequenceMatcher(None, norm_orig, norm_sub).ratio()

    # 自動判定等級
    if similarity >= 0.85:
        level = "minimal"
    elif similarity >= 0.55:
        level = "moderate"
    else:
        level = "significant"

    # 逐句比對找出具體改動
    changes = _extract_changes(original_lines, sub_sentences)

    # 產生摘要
    n_changes = len(changes)
    pct = round(similarity * 100)
    if n_changes == 0:
        summary = f"相似度 {pct}%，無明顯逐句差異"
    else:
        types = {}
        for c in changes:
            t = c.get("type", "modified")
            types[t] = types.get(t, 0) + 1
        parts = []
        if types.get("modified"):
            parts.append(f"{types['modified']} 句改詞")
        if types.get("added"):
            parts.append(f"{types['added']} 句新增")
        if types.get("removed"):
            parts.append(f"{types['removed']} 句刪除")
        summary = f"相似度 {pct}%，{'、'.join(parts)}"

    return {
        "similarity": round(similarity, 4),
        "level": level,
        "changes": changes,
        "summary": summary,
    }


def _extract_changes(orig_lines, sub_lines):
    """逐句對齊後提取具體改動。"""
    changes = []

    norm_orig = [_normalize(line) for line in orig_lines]
    norm_sub = [_normalize(line) for line in sub_lines]

    matcher = SequenceMatcher(None, norm_orig, norm_sub)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            # 逐對比對替換的句子
            for k in range(max(i2 - i1, j2 - j1)):
                orig = orig_lines[i1 + k] if (i1 + k) < i2 else ""
                sub = sub_lines[j1 + k] if (j1 + k) < j2 else ""
                if orig and sub:
                    changes.append({
                        "original": orig,
                        "actual": sub,
                        "type": "modified",
                    })
                elif orig:
                    changes.append({
                        "original": orig,
                        "actual": "",
                        "type": "removed",
                    })
                else:
                    changes.append({
                        "original": "",
                        "actual": sub,
                        "type": "added",
                    })
        elif tag == "delete":
            for k in range(i1, i2):
                changes.append({
                    "original": orig_lines[k],
                    "actual": "",
                    "type": "removed",
                })
        elif tag == "insert":
            for k in range(j1, j2):
                changes.append({
                    "original": "",
                    "actual": sub_lines[k],
                    "type": "added",
                })

    return changes


# ── 全自動流程 ────────────────────────────────────────────

def auto_diff_and_record(vid, subtitle_text):
    """完整流程：找腳本 → 提取口說 → 比對字幕 → 記錄偏差。

    Args:
        vid: 影片碼，如 VID-034
        subtitle_text: Kai 貼上的字幕全文

    Returns:
        (ok: bool, result: dict | str)
        成功時 result 含 diff 結果 + 記錄訊息；失敗時 result 為錯誤訊息。
    """
    # 1. 找腳本路徑
    data = load_pipeline()
    _, video = find_by_vid(data, vid)
    if not video:
        return False, f"找不到 {vid}"

    script_path = video.get("script_path")
    if not script_path:
        return False, f"{vid} 沒有 script_path，無法比對"

    full_path = PROJECT_ROOT / script_path
    if not full_path.exists():
        return False, f"腳本檔案不存在：{script_path}"

    # 2. 讀取腳本 + 提取口說行
    content = full_path.read_text(encoding="utf-8")
    spoken = extract_spoken_lines(content)
    if not spoken:
        return False, f"無法從腳本提取口說文字：{script_path}"

    # 3. 比對
    diff = diff_script(spoken, subtitle_text)

    # 4. 記錄
    ok, msg = record_deviation(vid, diff["level"], changes=diff["changes"])
    if not ok:
        return False, msg

    # 5. 自動連結 backfill 表現（若已回填）
    bf = video.get("backfill") or {}
    perf = bf.get("performance")
    if perf:
        link_performance(vid, perf)

    return True, {
        "similarity": diff["similarity"],
        "level": diff["level"],
        "changes": diff["changes"],
        "summary": diff["summary"],
        "record_msg": msg,
        "performance_linked": perf,
    }
