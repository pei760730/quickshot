# Brain Loading Protocol（v1.9）

> version: 1.9 | last_updated: 2026-05-17 | v1.9: kai_md 從必要（✅、FileNotFoundError 阻斷）→ optional（缺檔回空字串、不阻斷）、對齊實作層 `scripts/libs/brain_loader.py`（template 客戶尚未建 personas/ 時 generation skill 仍可跑、只是不注入人格）。連動 `02-skill-factory/quality/SKILL.md` + `02-skill-factory/discovery/SKILL.md` kai_md 欄位標記同步。v1.8: 清「§Orientation Phase 1」stale pointer（workflow.md v2.25+ 已升正式 §Orientation、本檔 2 處 active reference 同步清）。v1.7: BrainBundle 加 kai_md / an_md 欄位（v4.97 personas/ 拆分）。實作層 `scripts/libs/brain_loader.py` 已於 PR #432 接入（2026-05-11、`tests/test_brain_loader.py` regression tests 守護）。
> 所有生成類 skill 的「數據大腦載入」統一規範

## 本文件角色

統一 `02-skill-factory/` 下**生成類 skill** 的 Step 0 大腦載入規範。避免各 skill 自己寫讀取清單、造成漂移（/scan 發現的 H 級問題、已在 v4.47 前修過一次）。

**v1.5 重要變更**：`brand.md` / `cases.md` **不再由 session-start hook auto-inject**（v4.62 全文塞 retired）。所有載入路徑統一走 `brain_loader`：

- skill 跑時 → 本協議 `load_for_skill()` 取 BrainBundle
- 純對話中 Claude 需 brand context → 直接 `Read 01-data-brain/brand.md`（on-demand、單次）
- session-start hook 只印 1 行提示、不塞全文

理由：每 session 省 ~27k token baseline（brand 全文）+ skill 跑時去雙倍載入（hook + brain_loader 重複）。

## 為什麼

之前各 skill SKILL.md 的 stage 0 段落各自寫「讀 brand.md、讀 cases.md、讀 lessons.json（過濾 stage...）」、**12 份檔案重複 12 次**。任何規則變更（e.g. scope 過濾邏輯、origin 欄位新增）需要 12 處同步更新、容易漏。

解法：
- **Python 層**：`scripts/libs/brain_loader.py` 的 `load_for_skill(operator, skill_name) -> BrainBundle` 統一回傳
- **Prompt 層**（本檔）：各 skill SKILL.md 只寫「依 `shared-references/brain-loading.md` 載入」、不再寫具體清單

兩層對齊、SSoT 在本檔 + `brain_loader.py`。

## 載入清單（BrainBundle 內容）

依呼叫 `brain_loader.load_for_skill(operator, skill_name)` 取得：

| 欄位 | 必要 | 內容 | 失敗行為 |
|------|------|------|---------|
| `brand_md` | ✅ | `01-data-brain/brand.md` 全文（純品牌、v4.97 起 [3] / [12] 個人 section 已搬至 personas/）| `FileNotFoundError` 阻斷 |
| `kai_md` | — | `01-data-brain/personas/kai.md` 全文（主要創作者人格、檔名 hardcode 為 `kai.md`、選用）| 缺檔 → 空字串、不阻斷（lazy load fallback）|
| `an_md` | — | `01-data-brain/personas/an.md` 全文（對話搭檔 / 藏鏡人人格、選用）| 缺檔 → 空字串、不阻斷（lazy load fallback）|
| `cases_md` | ✅ | `01-data-brain/cases.md` 全文 | `FileNotFoundError` 阻斷 |
| `performance_patterns` | — | `data/<operator>/performance-patterns.json`（dict）| 缺檔 → 空 dict、不阻斷 |
| `lessons` | — | `data/<operator>/lessons.json.lessons[]` 過濾後 list | 缺檔 → 空 list、不阻斷 |
| `banned_words` | — | `02-skill-factory/shared-references/banned-words.md` 解析清單 | 缺檔 → 空 list、不阻斷 |

> **載入狀態**：`kai_md` / `an_md` 由 `scripts/libs/brain_loader.load_for_skill()` 自動載入進 BrainBundle、不需要 skill 端 lazy Read。兩者皆 optional、缺檔回空字串、不阻斷（template 客戶尚未建 personas/ 時 generation skill 仍可跑、只是不注入人格）。Regression 守護：`tests/test_brain_loader.py`。

## Lessons 過濾規則（SSoT）

`brain_loader` 自動應用、skill 端不再重複寫：

```
stage == "soft"
AND (scope 為空 OR skill_name ∈ scope OR "generation" ∈ scope)
```

**意思**：skill 只會收到「軟規則」（stage=soft、已 Kai 確認值得載入但未落成硬 artifact）且 scope 相關的。stage=hardened（已寫入 test/lint/禁令/brand、由 artifact 強制）或 archived（已退役）的不載入。

> ⚠️ **歷史 silent regression 紀錄**：`brain_loader.py:_active_lessons` 曾用已退役的 4 態 schema 過濾（`stage in ("candidate", "active")`）、導致所有 skill 載入 lessons = 0。已修復為 `stage == "soft"`、加 `tests/test_brain_loader.py` regression guard + `scripts/lint/rules-lint.py` 新規則防再犯。

## Skill prompt stage 0 引用格式

生成類 skill 在 SKILL.md 的 stage 0 段落寫：

```markdown
## 步驟 0：載入

依 `shared-references/brain-loading.md` v1.2 規範載入大腦、透過
`scripts/libs/brain_loader.load_for_skill("<operator>", "<this-skill-name>")`
取得 BrainBundle。必要欄位（brand / cases）缺失 → STOP。

### Lesson 使用標注（對應 workflow.md v2.9+ §對話中自然標注）
若本輪生成真的因某條 lesson 改寫 / 避開、對話結尾一句話自然標注（例：
「✓ 避開了 L-0023 的破折號殘留」）。不呼叫 CLI、不記計數（v4.63
lessons schema 降維、hit_count 已退役）。
```

具體欄位 / 過濾 / 失敗行為全在本檔、不再在 SKILL.md 重寫。

## 適用 skill（vNext 5 核心、Phase 5 對齊）

| Skill | mode/phase | 適用 | 備註 |
|-------|-----------|------|------|
| `discovery` | discover-week / discover-month / discover-trend | ✅ | 需全份 brand + cases + performance-patterns + lessons |
| `generation` | mode=dual-track | ✅ | T1 主生成器、需全份 |
| `generation` | mode=variant | ✅ | 變體器、同 dual-track |
| `generation` | mode=series | ✅ | 系列架構、需 [12] FAQ / 異常處理素材 |
| `generation` | mode=interview | ✅ | 對話壓力腳本、需 interview-bank.md |
| `generation` | mode=viral | ❌ | 知識型、不綁品牌（跳過 brand/cases、僅 lessons + banned-words）|
| `quality` | phase=check / phase=fix | ✅ | 使用 personas/kai.md [1] 說話風格（loader 選用、缺檔則 [1] 比對降級）+ lessons + banned-words |
| `orientation` | — | 退役 stub | v1.6 第二輪退役、規則回 workflow.md §Orientation；本協議僅在 Kai 真觸發 skill 時為相容性引用、不主動載入 |
| `distillation` | — | 退役 stub | v1.6 第二輪退役、三 phase 拆三層（workflow.md §Lesson 硬化提議 + session-start hook + `/harden` command）；本協議僅在 Kai 真觸發 skill 時為相容性引用 |

**不綁大腦**（跳過本協議）：
- `harden` command — 規則沉澱、不生成內容
- `skill-creator` — 官方 MCP 內建、不動
- Wave C tools（`scripts/tools/{web_fetch,research,trend}.py` 待寫）— 外部研究類、tool 層不走本協議

## 版本演進政策

- **v1.0**（2026-04-22）：Phase 3 建立、取代各 skill 分散寫法
- 未來 brain_loader 加 cache / 加 operator capability matrix / scope 過濾升級 → 本檔同步更新、skill SKILL.md 不需改（因 pointer 不變）

## Prompt × 實作對齊

- **Prompt 層**：skill prompt 讀本檔 pointer、執行時依 brain_loader 行為
- **Python 層**：`scripts/libs/brain_loader.py` 為實作、本檔為契約
- **任一側升級**：先改另一側同步（契約 → 實作 OR 實作 → 契約、雙向）

## 相關契約

- `docs/contracts/skill-io-schema.md` v1.2+ §Machine-readable Contract（skill IO 層、本協議是 Input 層的一部分）
- `docs/contracts/lessons-schema.md` v2.3（lessons 欄位定義、過濾邏輯的依據）

## Changelog

- **v1.0（2026-04-22）**：Phase 3 新建。對齊 `brain_loader.py`、收斂 6 個生成 skill 的 stage 0 敘述、避免未來再發生「stage 0 載入清單漂移」。
- **v1.1（2026-04-23）**：對齊 lessons-schema v2.0 降維（4 SKILL.md 的 stage 過濾補齊）、修 Stage C 殘留。
- **v1.2（2026-04-23、波次 4）**：§Lessons 過濾規則改寫（退役 candidate/active/observation 詞彙）、§Skill prompt stage 0 範本移除「Hit 網格（對應禁令 #8）」殘留（禁令 #8 於 CLAUDE.md v4.16 退役、Hit 機制 v4.63 降維）、外部契約版本 stale 引用更新。
- **v1.3（2026-04-25、Phase 5 對齊）**：§適用 skill 表從 14 個既有 skill 名重寫為 vNext 5 核心（discovery / generation 5 modes / quality / orientation / distillation）+ 對應 mode/phase + 載入策略。對應 engine v5.42-v5.44 退役 12 stub redirect。
- **v1.4（2026-04-29、第二輪退役對齊）**：§適用 skill 表中 orientation / distillation 標為退役 stub、實際規則回 workflow.md §Orientation + §Lesson 硬化提議 + session-start hook + `/harden` command。本協議下游剩 3 真 skill（discovery / generation / quality）為主要載入對象。對應 `docs/references/skill-architecture-principles.md` v1.6 §第二輪退役執行。
- **v1.5（2026-05-04、token cost 優化）**：`session-start.sh` brand.md auto-inject 退役（v4.62 全文塞 → lazy load）。所有載入路徑統一走 `brain_loader`：skill 跑時 `load_for_skill()`、對話中 Claude 需要時 `Read` on-demand。每 session 省 ~27k token baseline、skill 跑時去 hook + brain_loader 雙倍載入。配 7 陷阱對照（trap #3 hook 群體偷塞）優化第 1 步、無 schema 變動。
- **v1.6（2026-05-04、silent regression 修復對齊）**：`brain_loader.py:_active_lessons` 曾用已退役 4 態 schema（`("candidate", "active")`）、與本檔 §Lessons 過濾規則 SSoT（`stage == "soft"`）+ `lessons-schema` v2.3（3 態 soft/hardened/archived）矛盾、導致所有 skill lessons 命中 0%。修復：(1) `_active_lessons` 改 `stage == "soft"`、(2) `tests/test_brain_loader.py` regression guard、(3) `scripts/lint/rules-lint.py` 新規則防 stage 舊名再混入。
