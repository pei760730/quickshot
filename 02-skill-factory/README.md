# 02 - Skill Factory（Skill 工廠）

> **vNext 5 核心 skill + harden + skill-creator = 7 個 SKILL.md**（Phase 5 退役完成、2026-04-25）

## vNext 5 核心 skill

| 層級 | Skill | 版本 | 用途 |
|------|-------|------|------|
| **Core** | `orientation` | v2.0（stub）| 任務定型 — 第二輪退役、邏輯落於 `.claude/rules/workflow.md` §Orientation（規則層）|
| **Core** | `discovery` | v1.0 | 選題發現（外部熱點 + 大腦交互、3 modes：discover-week/month/trend）|
| **Core** | `generation` | v1.3 | 內容生產（5 modes：dual-track / variant / series / interview / viral）|
| **Core** | `quality` | v1.3 | 驗證 + 修（quality-loop pattern、phase=check + phase=fix）|
| **Core** | `distillation` | v2.0（stub）| 經驗沉澱 — 第二輪退役、三 phase 拆三層：collect-evidence 進 workflow.md §Distillation 對話準則 / propose 進 session-start hook / harden 進 `/harden` command |

**流程**：Orientation（task contract、規則層）→ 若 task=找選題 → Discovery → Generation → Quality → Distillation（三層分流、無單一 skill 入口）。
若 task=拍既有選題 → 跳過 Discovery、直接 Generation → Quality → Distillation。

## 配套 skill

| 層級 | Skill | 版本 | 用途 |
|------|-------|------|------|
| Tool | `harden` | v2.1 | 對話內一站式硬化（soft lesson → test/lint/CLAUDE.md/workflow.md/brand.md）|
| Locked | `skill-creator` | — | 官方 MCP 內建（封版、不在本系統維護範圍）|

## 調用方式

透過 `.claude/skills/` entry files 按需載入、不需每次讀全部 SKILL.md。

新 keyword（`下週要拍什麼` / `discovery` / `generation mode=...` / `驗證` / `/harden`）啟動 vNext 核心 skill。

## 版本歷史

集中記錄於 `02-skill-factory/CHANGELOG.md`（非 per-skill）。

## vNext 設計依據

詳見：
- `docs/references/skill-architecture-principles.md` v1.3+ §vNext（必要能力 A-G + 失敗模式 F1-F7 + 5 核心 skill 推導）
- `docs/references/skill-consolidation-map.md` v1.1+（14 → 5 完整對應 map）
- `02-skill-factory/shared-references/skill-design-principles.md` v1.5+（A/B/C/D/E/F 六準則、F 為 4.7 mature 視角新增）
- `CLAUDE.md` 禁令 #12（skill 成立 10 條件）

---

**版本**：v6.3
**最後更新**：2026-04-30
