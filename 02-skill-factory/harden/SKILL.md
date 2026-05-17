---
name: harden
description: harden v2.1 — 對話內一站式硬化的 spec doc。把 soft lesson 或反覆錯誤升為 test / lint / CLAUDE.md 禁令 / workflow.md 規則 / brand.md section。實際入口：`.claude/commands/harden.md`、實作：`scripts/ops/lib/hardening.harden_from_dialog()`。本檔為 spec、命令層直接呼叫不經過 SKILL load。
version: 2.1
last_updated: 2026-04-30
---
<!-- v2.0 → v2.1（2026-04-30）：原 v2.0 stub 引用 distillation/SKILL.md phase=harden、但 distillation 在 Phase 6 第二輪退役後已成 v2.0 stub（workflow.md v2.25 §Distillation 三 phase 拆三層）。本次更新把 redirect 目標改為實際 live 路徑（command + lib）-->
<!-- 對應 docs/references/skill-architecture-principles.md v1.6 §第二輪退役執行 + workflow.md v2.25 §Distillation 三 phase 拆三層 -->

# harden v2.1（spec for `/harden` command）

> 本檔是 `/harden` 指令的 spec 參考。實際觸發 / 流程在 `.claude/commands/harden.md`、實作在 `scripts/ops/lib/hardening.harden_from_dialog()`。
> Claude 對話中執行 `/harden` 時會用 command 規格、不會 load 本 SKILL.md（command 直接呼叫 Python lib）。

---

## 觸發

Kai 在對話中：
- `/harden L-XXXX [path]`
- `升 L-XXXX 為 <path>`
- `硬化 L-XXXX`

或 Claude 觀察到 soft lesson 反覆出現、提議升 hardened、Kai 同意。

---

## 5 種硬化路徑

| path | 落點 | 適用 lesson 類型 |
|------|------|----------------|
| `test` | `tests/test_*.py` | 程式邏輯錯誤 / schema 違反 / 跨檔一致性 |
| `lint` | `scripts/lint/rules-lint.py` 新規則 | 文字模式 / 命名 / 引用一致性 |
| `claude_md` | `CLAUDE.md` 禁令 | 對話行為紅線 / always-on 規則 |
| `workflow_md` | `.claude/rules/workflow.md` 段落 | 流程 / 觸發條件 / 對話規範 |
| `brand_md` | `01-data-brain/brand.md` 對應 section | 品牌事實 / 競品紅線 / 禁忌邊界 |

---

## 流程（command 執行步驟）

1. Claude 讀 lesson `pattern` + `counter_pattern`、草擬 artifact 內容
2. 展示 draft + target path 給 Kai 確認
3. 呼叫 `scripts/ops/lib/hardening.harden_from_dialog()` → 寫檔 + validator
4. **成功**：lesson `stage = "hardened"`、寫 `data/[op]/hardening-archive.json`（source="dialog"）
5. **失敗**：lesson 保留 `soft`、archive 不寫、回報原因（不污染狀態）

---

## 為什麼從 v1.x 升 v2.x

- v1.x：harden 是 14 skill 之一
- v2.0（2026-04-25 Phase 3+4）：vNext 收斂試圖把 harden 合併進 distillation 的 phase=harden
- v2.1（2026-04-30 Phase 6 第二輪）：distillation 自身降 stub、harden 改回 standalone via command — 三 phase 拆三層後、harden 變獨立指令

詳見 `02-skill-factory/CHANGELOG.md` + `docs/references/skill-architecture-principles.md` v1.6 §第二輪退役執行。

---

## 相關文件

- `.claude/commands/harden.md`：command 入口（Claude 對話實際讀此檔）
- `scripts/ops/lib/hardening.py`：`harden_from_dialog()` 實作
- `data/[op]/hardening-archive.json`：成功記錄（source="dialog"、稽核用）
- `docs/references/skill-architecture-principles.md` v1.6+：第二輪退役脈絡
- `.claude/rules/workflow.md` v2.25+ §Lesson 硬化提議：對話準則層

<!-- 版本歷史見 02-skill-factory/CHANGELOG.md -->
