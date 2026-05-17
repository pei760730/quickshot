#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mistake recording helper — 寫入 lessons.json（統一 lessons API）。

v4.36 起 `data/skill-memory/claude-mistakes.json` 三檔合併入 `lessons.json`。
v4.78 清除 legacy API（load_mistakes / save_mistakes / archive_graduated_mistakes
+ _mistakes_json / _archive_dir）— 路徑已不存在、呼叫永遠 no-op。
本模組僅保留 `record_mistake()` 作為 `記錯` CLI 的寫入通道、內部呼叫 add_lesson。
"""

from .lessons import add_lesson


def record_mistake(operator, description, correct_behavior=None, context=None, stage="soft"):
    """將 mistake 寫入 lessons.json（origin=mistake）。"""
    return add_lesson(
        operator=operator,
        origin="mistake",
        pattern=description,
        counter_pattern=correct_behavior,
        evidence=[],
        scope=[],
        stage=stage,
        source_note=context,
    )
