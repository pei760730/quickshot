---
name: orientation
description: orientation v2.1（第二輪退役 stub） — 真實邏輯回歸 `.claude/rules/workflow.md` §Orientation（規則層、不在 skill 層）。本檔保留為 stub 維持 lint invariant + brain_loader 引用穩定。實際 task contract 規則見 workflow.md。
version: 2.1
last_updated: 2026-05-15
brand-refs: []
---
<!-- 第二輪退役 stub — 對應 docs/references/skill-architecture-principles.md v1.6 §第二輪退役執行（5 → 3 真 skill） -->
<!-- v1.0 內容（task contract / 三層強度 / 載入規範）已歸位 .claude/rules/workflow.md §Orientation -->

# orientation v2.1（第二輪退役 stub）

> ⚠️ **本 skill 已退役為 stub**、實際邏輯在 `.claude/rules/workflow.md` §Orientation。
> 本檔保留是為了：
> 1. 維持 lint invariant（disk_missing_skill 不 fire）
> 2. `.claude/skills/orientation.md` redirect 穩定
> 3. brain-loading.md §適用 skill 表引用穩定

---

## 為什麼退役

對應 `docs/references/skill-architecture-principles.md` v1.6 §第二輪退役執行：

- v1.4 §第二輪退役預備條款已預判：Orientation 通過準則 F 第 1 層（對話準則層）即可、升 SKILL.md 是 4.7 初期慣性
- v1.5 揭露觀察期數據（trace 採用率）永久空轉、4 條觀察期 metric 收不到 → first-principles 直判、不等
- task contract 的核心邏輯（5 必含 + 1 條件元素 / 三層強度 / 載入規範）回歸 workflow.md §Orientation（已存在、跑得起來）、與其他對話準則同層、降低 skill 框架的維護負擔
- 「Phase 1」字樣的去除（升正式 §Orientation）為 Kai 授權 .claude/ 編輯後 follow-up、不影響本退役決策

---

## 觸發方式

Kai 觸發新 task 時、Claude 依 `.claude/rules/workflow.md` §Orientation 執行 task contract。

不需要 skill 框架介入、規則層即足。

---

## 真退役時機（未來）

待以下穩定後、本 stub 可真正刪除：
- workflow.md §Orientation 跑了 1-2 個月、未發生「規則太長 / 三層強度判斷不穩」訊號
- `.claude/skills/orientation.md` 連同移除
- canonical-registry.json valid_skills 移除 orientation

短期不刪、stub 維持 sync-engine 對齊。

---

## 相關文件

- `.claude/rules/workflow.md` §Orientation：實際規則
- `docs/references/skill-architecture-principles.md` v1.6+：第二輪退役決策
- `02-skill-factory/shared-references/skill-design-principles.md` 準則 F（4 層退場測試）

<!-- 版本歷史見 02-skill-factory/CHANGELOG.md -->
