---
name: distillation
description: distillation v2.0（第二輪退役 stub） — 三 phase 拆三層回歸：collect-evidence 進 `.claude/rules/workflow.md` §Distillation 對話準則、propose 進 session-start hook（lesson-pressure）、harden 進 `/harden` command。本檔保留為 stub 維持 lint invariant + brain_loader 引用穩定。
version: 2.0
last_updated: 2026-04-29
brand-refs: []
---
<!-- 第二輪退役 stub — 對應 docs/references/skill-architecture-principles.md v1.6 §第二輪退役執行（5 → 3 真 skill） -->
<!-- v1.0 三 phase 拆三層歸位：對話準則 + hook + command、不再塞同一 skill -->

# distillation v2.0（第二輪退役 stub）

> ⚠️ **本 skill 已退役為 stub**、實際邏輯按 phase 觸發模型分拆三層。
> 本檔保留是為了：
> 1. 維持 lint invariant（disk_missing_skill 不 fire）
> 2. `.claude/skills/distillation.md` redirect 穩定
> 3. brain-loading.md §適用 skill 表引用穩定

---

## 三 phase 拆三層

| Phase | 觸發模型 | 落點 |
|-------|---------|------|
| **collect-evidence**（被動累積）| 對話中、任何 task 內 | `.claude/rules/workflow.md` §Lesson 硬化提議 §對話中累積 evidence + §對話期間的進化提案 |
| **propose**（提硬化候選） | session-start hook 自動掃 + 對話中 Claude 主動提 | `.claude/hooks/session-start.sh` lesson-pressure 區段 + workflow.md §Lesson 硬化提議 §硬化提議 |
| **harden**（規則沉澱）| Kai 顯式呼叫 | `.claude/commands/harden.md` + `02-skill-factory/harden/SKILL.md` v2.0 |

三個 phase 觸發模型完全不同（被動累積 / 跨 session 偵測 / 顯式 command）、塞同一 skill = 「skill-as-folder」非「skill-as-capability」、違反準則 F。

---

## 為什麼退役

對應 `docs/references/skill-architecture-principles.md` v1.6 §第二輪退役執行：

- v1.4 §第二輪退役預備條款已預判：Distillation 通過準則 F 1+2+3 層組合、不該塞單一 skill
- v1.5 揭露觀察期數據空轉、不等實際命中率、first-principles 直判
- 三 phase 各自落點都是現有機制（workflow.md 段落 / session-start hook / `/harden` command）、不需新建 skill 框架

---

## 觸發方式

| Kai 說 | 落點 |
|-------|------|
| `記錯：XXX` / 對話中真的避開 lesson | workflow.md §Lesson 硬化提議 §對話中累積 evidence |
| `提硬化` / hook 印「💡 候選硬化」| workflow.md §Lesson 硬化提議 §硬化提議 |
| `升 L-XXXX` / `硬化 L-XXXX` / `/harden` | `02-skill-factory/harden/SKILL.md` v2.0 |
| 對話中提到新品牌事實 | workflow.md §對話期間的進化提案 |

不需 skill 框架介入、各層自然觸發。

---

## 真退役時機（未來）

待以下穩定後、本 stub 可真正刪除：
- workflow.md §Distillation 跑了 1-2 個月、三 phase 落點穩定
- `.claude/skills/distillation.md` 連同移除
- canonical-registry.json valid_skills 移除 distillation

短期不刪、stub 維持骨架供日後升回。

---

## 相關文件

- `.claude/rules/workflow.md` §Lesson 硬化提議 + §對話期間的進化提案：collect / propose 規則（未來 Kai 授權 .claude/ 編輯後可整理為 §Distillation 統一段、本 follow-up 不影響本退役決策）
- `.claude/hooks/session-start.sh` lesson-pressure：cross-session propose 偵測
- `02-skill-factory/harden/SKILL.md` v2.0：harden phase 實際邏輯（從 v1.0 起即在 harden、不在本 skill）
- `docs/references/skill-architecture-principles.md` v1.6+：第二輪退役決策
- `02-skill-factory/shared-references/skill-design-principles.md` 準則 F（4 層退場測試）

<!-- 版本歷史見 02-skill-factory/CHANGELOG.md -->
