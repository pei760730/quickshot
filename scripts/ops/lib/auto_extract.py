#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腳本/逐字稿自動解析：開場類型、CTA、轉折點。
"""

import re

from .config import PROJECT_ROOT


# ── 腳本正文解析（共用）─────────────────────────────────

_SKIP_PREFIXES = ("以下皆為", "以下為", "旁白", "（", "---")


def _parse_script_body(content):
    """從腳本/逐字稿內容解析正文行（跳過 metadata + 註解）。

    回傳 list[str]（已 strip），空內容回傳空 list。
    """
    lines = content.splitlines()

    body_start = 0
    in_metadata = True
    for i, line in enumerate(lines):
        if in_metadata:
            stripped = line.strip()
            if stripped == "---":
                in_metadata = False
                continue
            # blockquote metadata（> 影片碼：...）也視為 metadata
            if stripped.startswith(">") or not stripped:
                continue
            # 遇到非空、非 blockquote、非 --- 的行 → metadata 結束
            in_metadata = False
            body_start = i  # 這行本身就是正文開始
        if line.startswith("## ") or line.startswith("以下"):
            body_start = i + 1
            break

    return [
        s for line in lines[body_start:]
        if (s := line.strip()) and not s.startswith(">") and not s.startswith("#")
        and not any(s.startswith(p) for p in _SKIP_PREFIXES)
    ]


# ── 輕量 G3 平台適配性分析（quick-shot 回填後自動觸發）────

# 模組層級預編譯（與 _OPENING_PATTERNS / _CTA_PATTERNS / _TURNING_WORDS 同級）
_G3_HOOK_SIGNALS = re.compile(
    r"(\d+[萬千億]|[0-9,]+萬|[？?]|但是|沒想到|竟然|到底|為什麼|怎麼可能|危機|賠|倒閉|虧)"
)


# ── 開場/CTA 關鍵字對照 ──────────────────────────────────

# 開場類型關鍵字對照（priority 越小越優先）
_OPENING_PATTERNS = [
    ("D3", 1, re.compile(r"\d+[萬千億]|[0-9,]+萬")),
    ("D1", 2, re.compile(r"(結果|最後|後來).{0,10}(卻|竟然|沒想到)")),
    ("B1", 3, re.compile(r"(危機|停業|倒閉|賠了|虧了|出事)")),
    ("B2", 4, re.compile(r"(你知道|到底|為什麼|怎麼可能|竟然)")),
    ("B3", 5, re.compile(r"(你覺得|你認為|站哪邊|選哪個)")),
    ("D2", 6, re.compile(r"(你有沒有|是不是|難道).*[?\？]")),
]

# CTA 類型關鍵字對照（priority 越小越優先）
_CTA_PATTERNS = [
    ("C1", 1, re.compile(r"(你覺得|你認為|你站哪|選哪)")),
    ("C2", 2, re.compile(r"(按讚|收藏|儲存|分享)")),
    ("C3", 3, re.compile(r"(留言|告訴我|說說|評論)")),
    ("C4", 4, re.compile(r"(下集|下一集|下次|追蹤|關注)")),
]

# 轉折詞
_TURNING_WORDS = re.compile(r"(但是|但|沒想到|結果|關鍵是|真相是|後來|卻)")


def _best_match(patterns, text):
    """從 patterns 列表匹配全部，取 priority 最小（最優先）+ match span 最長的。"""
    matches = []
    for code, priority, pat in patterns:
        m = pat.search(text)
        if m:
            matches.append((priority, -(m.end() - m.start()), code))
    if not matches:
        return None
    matches.sort()  # (priority asc, -span desc, code)
    return matches[0][2]


def _lite_g3_check(script_path):
    """對腳本做輕量 G3 分析，回傳問題清單。不阻塞流程，僅供參考。"""
    if not script_path:
        return None
    full_path = PROJECT_ROOT / script_path
    if not full_path.exists() or full_path.is_dir():
        return None

    try:
        content = full_path.read_text(encoding="utf-8")
    except OSError:
        return None

    body_lines = _parse_script_body(content)
    if not body_lines:
        return None

    issues = []

    # 檢查 1：前 3 行是否有 hook（複用 _G3_HOOK_SIGNALS，與 _OPENING_PATTERNS 關鍵字對齊）
    first_3 = "".join(body_lines[:3])
    if not _G3_HOOK_SIGNALS.search(first_3):
        issues.append("前 3 行缺少明顯 hook（無數字/問句/衝突詞）")

    # 檢查 2：最後 5 行是否有 CTA（複用 _CTA_PATTERNS，確保關鍵字單一來源）
    last_5 = "".join(body_lines[-5:])
    has_cta = any(pat.search(last_5) for _, _, pat in _CTA_PATTERNS)
    if not has_cta:
        issues.append("結尾缺少 CTA / 互動引導")

    # 檢查 3：是否有情緒轉折（複用 _TURNING_WORDS）
    has_turning = any(_TURNING_WORDS.search(line) for line in body_lines)
    if not has_turning:
        issues.append("全篇缺少情緒轉折點")

    return {
        "issues": issues,
        "pass": len(issues) == 0,
        "checked_items": ["3秒hook", "CTA互動", "情緒轉折"],
    }


def auto_extract_from_script(script_path, transcript=None):
    """從腳本檔案自動解析學習特徵。

    若 script_path 不存在但有 transcript，則從 transcript 解析。

    回傳 dict:
    {
        "hook": "前幾行對白",
        "opening_guess": "D3",
        "cta_guess": "C4",
        "turning_points": ["但是...句子"],
        "formula_hint": "數字衝擊→...→...",
    }
    若檔案不存在且無 transcript，回傳 None。
    """
    script_content = None
    if script_path:
        full_path = PROJECT_ROOT / script_path
        if full_path.exists() and not full_path.is_dir():
            try:
                script_content = full_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass

    transcript_content = transcript if transcript else None

    # 至少需要一個來源
    if script_content is None and transcript_content is None:
        return None

    # Hook/Opening 優先用腳本（打磨版），CTA 優先用逐字稿（實際結尾）
    hook_source = script_content or transcript_content
    cta_source = transcript_content or script_content

    parsed_cache = {}

    def _get_parsed_lines(source):
        if source not in parsed_cache:
            parsed_cache[source] = _parse_script_body(source)
        return parsed_cache[source]

    hook_lines = _get_parsed_lines(hook_source)
    cta_lines = _get_parsed_lines(cta_source)

    if not hook_lines and not cta_lines:
        return None

    # 如果其中一方為空，fallback 到另一方
    if not hook_lines:
        hook_lines = cta_lines
    if not cta_lines:
        cta_lines = hook_lines

    result = {}

    # Hook：前 5 行非空白文字合併（from script）
    result["hook"] = "".join(hook_lines[:5])

    # 開場類型猜測：用前 10 行判斷（from script）
    opening_text = "".join(hook_lines[:10])
    result["opening_guess"] = _best_match(_OPENING_PATTERNS, opening_text)

    # CTA 猜測：用最後 10 行判斷（from transcript = 實際結尾）
    cta_text = "".join(cta_lines[-10:])
    result["cta_guess"] = _best_match(_CTA_PATTERNS, cta_text)

    # 轉折點：找含轉折詞的句子
    turning_points = []
    for line in hook_lines:
        if _TURNING_WORDS.search(line) and len(line) > 3:
            turning_points.append(line)
    result["turning_points"] = turning_points[:3]  # 最多 3 個

    return result
