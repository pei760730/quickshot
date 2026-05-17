# Skill Factory CHANGELOG

> 7 個 skill 的版本歷史集中記錄（5 核心 + harden + skill-creator、Phase 5 退役後）。
> 最新在最上面。系統級變更見 `07-changelog/CHANGELOG.md`。

---

## 2026-05-05 — generation v1.2 → v1.3 + quality v1.2 → v1.3（trace/verifier 0/30 採用閉環行為層補）

**主題：「呼叫 CLI」模糊動詞 → 硬性「Bash tool 執行、禁止印命令給 Kai 抄」**

**根因**：v1.1 PR #348 加 `trace_required_statuses` CLI 強制、v1.2 把人話層升主視覺、但 `generation_trace 0/30、verifier_scores 0/30 over 30 days`。讀現況發現 §Output Contract 寫「呼叫 CLI」+ 印 Bash code block — 這格式在 Claude 對話中常被解讀為「展示給 Kai 抄」（4.6 慣性「Claude = 顧問、不是執行者」）、不是「Bash tool 立刻執行」。trace 0/30 的真實根因是動詞模糊。

**修法**：
- generation v1.3：§Output Contract 4 階段壓 3 階段、§1 從「AI 自評 4 句」改「**Bash tool 執行 save**」、移除 fenced JSON 中介層、trace 直接 inline 進 --trace heredoc arg。§反例新增「印 Bash code block 給 Kai 看」+「印 fenced JSON 給 Claude 自己看」兩條 anti-pattern。
- quality v1.3：§Output Contract §1 從「呼叫 CLI」改「**Bash tool 執行 record-verifier-scores**」、加「禁止印命令給 Kai 抄」硬性動詞。§反例新增「印 Bash code block 給 Kai 看」anti-pattern。

**對應**：`docs/references/skill-architecture-principles.md` v1.5 補注「機械擋下 ≠ 行為改變」第二層補正 — 不只 CLI 強制、還要 SKILL.md 動詞硬化。

**14 天觀察 metric**：
- `generation_trace`: 0/30 → 目標 ≥40%
- `verifier_scores`: 0/30 → 目標 ≥40%
- 不到閾值 = §4.A 假設也錯、要追下一層 root cause（可能是 Kai 工作流根本不走 generation skill / Claude 對話中執行 Bash 仍有 friction）

**沒做也沒打算做**（v5.87 主 commit 原立場、follow-up 部分推翻）：
- ~~不升 CLAUDE.md 禁令 #15「CLI 強制 ≠ 行為改變」~~ → reframe 為 workflow.md §設計原則 Mode W、避開「禁令本身禁止再加禁令」矛盾。**待 .claude/ 權限授權後補**。
- ~~不寫 architecture-principles.md v1.7 補注「§盲點 3 反證」~~ → reframe 為「記錄已觀察反證、不預測 v1.3 解成功」。**follow-up commit 已補 v1.7**、過了 v1.6.3 元規則三條件檢查、不違反禁令 #13。
- 14 天 metric 仍是 hard exit 條件、與本 follow-up 不衝突

### Second follow-up（Kai 命「再深看一次」、漏網修補）

深掃發現 v5.87 主 commit 漏修同根因第二處：3 個 SKILL.md 的「Lesson 使用標注」段「同步呼叫 `video-ops.py lessons add-evidence`」是同類動詞模糊。真實 evidence 採用率 11.7%（4/34、且多為 PR# / incident#、非 SKILL.md 觸發）— 同 trace 0/30、verifier 0/30 同構失敗。

**修法**（generation / quality / discovery SKILL.md 同模式）：「同步呼叫」→「使用 Bash tool 直接執行」+「禁止印命令給 Kai 看」、不 bump 版本（小改、同 v5.87 邏輯主題）。

**連帶影響**：lesson-pressure hook 化（P2、workflow.md v2.10+）整條管線之前事實上未運作、本修是 P2 真正的行為層落地。

**未修**：`workflow.md §對話中累積 evidence` 同類動詞「呼叫」、受 .claude/ 權限保護、加入 Mode W 待授權清單一併補。

---

## 2026-05-04 — brain-loading.md v1.5 → v1.6（PR #365 silent regression 修復對齊）

**主題：lessons stage filter drift 修復後、契約層紀錄根因 + reframe v1.0 §發現 B**

### 背景

深掘 `brain_loader.py` 揭露：`_active_lessons` 從 PR #365（2026-04-29）起用已退役的 4 態 schema：

```python
def _active_lessons(rows):
    return [row for row in rows if row.get("stage") in ("candidate", "active")]
```

但：
- `lessons-schema` v2.3 / `data/kai/lessons.json` 實際 stage 值為 `soft / hardened / archived`
- 本檔 v1.2 §Lessons 過濾規則 SSoT 寫 `stage == "soft"`

導致 31 條 lessons 中 24 條 soft 對所有 skill 命中 0%、6 天內無 test 抓到（因為 bundle.lessons = 0 不 raise、看似「沒 soft lessons」）。

### Reframe v1.0 §發現 B

`docs/references/skill-architecture-principles.md` v1.0 §發現 B「lessons 從進化前導退化為事後審計」原解釋為「Kai 直接寫 CLAUDE.md 禁令、lesson 層空轉」（設計層問題）。

本次深掘揭露真因 = **實作層 silent regression、非設計層**：
- skill 載入 lessons = 0 不是因為機制差、是因為 brain_loader filter 抓不到 soft
- Kai 看到的「lesson 沒被應用」是真實現象、根因是 code bug

→ v1.0 §發現 B 結論需修正、待修復後 1-2 週觀察期重新評估 lesson 機制是否仍需重設計。

### 配套（Codex PR `codex/fix-brain-loader-stage-drift`）

| 檔 | 動作 |
|----|------|
| `scripts/libs/brain_loader.py:82-83` | `("candidate", "active")` → `"soft"` |
| `tests/test_brain_loader.py`（新檔）| 4 個 test：filter soft only / reject legacy stages / empty input / smoke test load_for_skill |
| `scripts/lint/rules-lint.py` | 新規則：偵測非 migration 檔出現 stage 舊名（candidate/active/observation）→ warning |

### 本檔變更

| 項目 | v1.5 | v1.6 |
|------|------|------|
| header | v1.5 / brand.md auto-inject 退役 | v1.6 / 紀錄 PR #365 silent regression 修復 |
| §Lessons 過濾規則 | 純規則 + 意思 | 加 ⚠️ v1.6 修正紀錄段、紀錄 PR #365 → v5.83 期間的 silent regression、配套 Codex PR + lint rule |
| Changelog | v1.5 entry | 加 v1.6 entry |

### 為什麼

- contract 與 implementation 任一側升級必雙向同步（本檔 §跨代理協作 已寫此原則、本次反例 6 天未察覺）
- silent regression 對 learning loop 影響極大（lesson 是 4.7 推理力的軟規則前導）、必紀錄根因 + 防再犯機制
- 對齊 v1.0 §發現 B 結論的 reframe 需求

### 相關 lesson

`L-NEW`（origin=mistake、stage=hardened、scope=['engine', 'brain-loader']）：
- pattern: schema 降維後 6 天內 brain_loader code 仍用舊 stage 名、契約 SSoT 寫 soft、code 寫 candidate/active、無 test 對齊
- counter_pattern: schema 降維後立即跑 grep 全 repo + 對中央 reader（brain_loader）寫 contract test + 加 lint 規則防舊名混入

### 不做（保守）

- 本 PR 不處理 #2-#8 其他 drift（Task B 後續 Codex PR）
- engine-manifest brain-loading.md 1.5 → 1.6 + engine_version 5.83 → 5.84 同 PR 處理（cross-territory bump、本 PR 預授 override）

---

## 2026-05-04 — brain-loading.md v1.4 → v1.5（brand.md auto-inject 退役、改純 lazy load）

**主題：token cost 優化第 1 步 — 配 7 陷阱對照（trap #3 hook 群體偷塞）**

### 背景

`.claude/hooks/session-start.sh` 自 v4.62 起把 `01-data-brain/brand.md` 全文（~27k token、約 18k 字）每 session cat 進 context、不論 task 類型。同時 `scripts/libs/brain_loader.py` 已存在（Phase 3 PR #225）做 skill 跑時的結構化載入 — **雙倍載入**（hook 一次 + brain_loader 一次）。

7 陷阱對照本 repo baseline 量測（CLAUDE.md 24k + workflow.md 48k + brand.md 27k + 其他 ≈ 103k token / session）後判定：brand.md auto-inject 是最高槓桿單點優化（純工程對話 100% 白繳 27k、skill 對話雙繳 54k）。

### 變更

| 檔 | 動作 |
|----|------|
| `.claude/hooks/session-start.sh` | 拿掉 `cat "$BRAND"` 全文塞、改 1 行提示「💡 brand.md 改 lazy load... → skill 跑時 brain_loader 自動載；對話需要時 Read」 |
| `02-skill-factory/shared-references/brain-loading.md` | v1.4 → **v1.5**：§本文件角色 加 v1.5 重要變更段、§Changelog 新增 v1.5 entry |
| `CLAUDE.local.md` | §品牌速查 從「v4.62+ 全文 auto-inject」改為「lazy load」+ 三層觸發路徑（skill / 對話 / hook） |
| `engine-manifest.json` | engine 5.82 → 5.83、brain-loading.md 1.4 → 1.5、CHANGELOG 5.82 → 5.83 |
| `07-changelog/CHANGELOG.md` | 本變動的 engine entry |

### 為什麼

- 量測：每 session baseline 含 brand.md 全文 = ~103k token；本變動後降至 ~76k（−27k、−26%）
- 純工程對話（佔總對話估 30-50%）100% 受益 — 不跑 skill 就不載 brand
- skill 對話去雙倍載入（從 54k → 27k）
- 身份識別不掉 — CLAUDE.local.md 的品牌名 / operator / forbidden_terms 仍每 session auto-load
- 對話中 Claude 需 brand context 推理時、`Read 01-data-brain/brand.md` on-demand 即可、單次成本 ≤ 雙倍載入

### 對應 4.7 mature 視角

`docs/references/skill-architecture-principles.md` v1.6 元規則 + 工作模式 Z（批判上次審視）：v4.62 「衍生速查檔已廢除、改全文 auto-inject」是 4.6 慣性 — 假設「載入越多越安全」。4.7 推理力下、lazy load + skill on-demand 已足、Pre-load 是反向浪費。

### 不做（保守）

- 不拆 brand.md 為 brand-core / brand-cases（避免兩檔同步成本）
- 不在 hook 加 task-type 偵測（判斷邏輯本身是新負擔）
- 各 SKILL.md 的 brain_loader pointer 不變（行為層已正確）
- brand.md 本體 100% 不動

### 驗證

- `bash -n .claude/hooks/session-start.sh` ✓
- 下次新對話：session 開頭應只剩 1 行 brand 提示 + adoption gate、無 27k 全文
- 跑 generation/quality skill 時 brain_loader 仍正常返 BrainBundle

### 後續優化（不在本 PR）

- Trap #1：CLAUDE.md / workflow.md 版本史下沉 design-lineage.md（~−35k baseline）
- Trap #4：1 小時 prompt cache 配置
- Trap #5：MCP server 審計

---

## 2026-04-30 — harden SKILL.md v2.0 → v2.1（redirect 對齊修正）

**主題：sleep-mode fact realignment、修正 v2.0 stub 引用已退役 skill 的 broken redirect**

### 背景

`02-skill-factory/harden/SKILL.md` v2.0（2026-04-25 Phase 3+4）原 stub 內容：「本 skill 已退役為 stub、實際邏輯在 `02-skill-factory/distillation/SKILL.md` v1.0+ 的 phase=harden」。

但 2026-04-29 Phase 6 第二輪退役執行後、`distillation/SKILL.md` 自身降為 v2.0 stub（三 phase 拆三層、`/harden` 從 distillation 拆出成獨立 command）— 結果 harden stub 指向另一個 stub、redirect 鏈斷。

### 變更

| 項目 | v2.0 | v2.1 |
|------|------|------|
| description | 「升級為 Distillation Skill 主體、合併進 distillation/SKILL.md 的 phase=harden」 | 「對話內一站式硬化 spec doc、實際入口 `.claude/commands/harden.md`、實作 `scripts/ops/lib/hardening.harden_from_dialog()`」 |
| body | redirect → `distillation/SKILL.md v1.0+`（已退役）| spec → 5 種硬化路徑表 + 流程 + v1.x→v2.x 演化脈絡 |
| 觸發定位 | 員工觸發舊名 redirect | command + lib 直接觸發、本檔為 spec 參考 |

### 為什麼

- 原 stub redirect 目標已退役（distillation v2.0 stub）→ broken redirect chain
- `/harden` 命令層仍 alive、實際讀 `.claude/commands/harden.md`、不 load 本 SKILL.md
- 本檔回歸 spec doc 角色、保留版本標籤一致性 + lint invariant

### 不在範圍（permission-denied）

- `.claude/skills/harden.md` stub description 對齊 v2.1（受保護）
- `.claude/commands/harden.md` 結尾「完整規格見 02-skill-factory/harden/SKILL.md v1.0」應改 v2.1（受保護）
- `.claude/rules/workflow.md` line 230 / 443「v1.2」應改 v2.1（受保護）

待 Kai UI 授權批次清。

---

## 2026-04-29 — 第二輪退役執行：Orientation + Distillation v2.0 stub（5 → 3 真 skill）

**主題：v1.4 §第二輪退役預備條款執行（不等觀察期、first-principles 直判）**

### 退役清單（2 個 SKILL.md 降 stub）

| Skill | 原版本 | 落點 | 為什麼 |
|-------|-------|------|------|
| orientation | v1.0 | workflow.md §Orientation Phase 1（規則層） | 通過準則 F 第 1 層、對話準則層即可、升 SKILL.md 是 4.7 初期慣性 |
| distillation | v1.0 | workflow.md §Lesson 硬化提議 + session-start hook + `/harden` command（三層） | 三 phase 觸發模型完全不同、塞同一 skill = 「skill-as-folder」 |

### 為什麼提前執行（不等 v1.4 「1-2 月觀察期」）

v1.5 揭露 `generation_trace` 0/61、`verifier_scores` 0/61、`hook_type` 13/61。觀察期 4 條 metric 全依賴 trace 累積、chicken-and-egg trap。first-principles 直判：v1.4 結論已正確、執行即可。

### 配套變更

- `02-skill-factory/shared-references/brain-loading.md` v1.3 → v1.4（§適用 skill 表標 stub）
- `docs/references/skill-architecture-principles.md` v1.5 → v1.6（補注 + 元規則「研究退場條件」）
- engine-manifest.json：engine_version 5.66 → 5.67、4 個 contract_files version 同步

### 不在本變更範圍（待 .claude/ 授權後 follow-up）

- `.claude/skills/orientation.md` + `.claude/skills/distillation.md` description 更新
- `.claude/rules/workflow.md` §Orientation Phase 1 → §Orientation 正式版 + §Distillation 統一段

不影響功能：SKILL.md stub 指向 workflow.md 既存段落、原本就跑得起來。

### 真退役時機（未來）

3-6 週後若 Kai 工作流確實不再觸發 orientation / distillation 名稱、考慮：
- 整刪 02-skill-factory/orientation/ + 02-skill-factory/distillation/ 目錄
- 整刪 .claude/skills/orientation.md + .claude/skills/distillation.md
- canonical-registry.json valid_skills 移除兩名（Codex 領土、follow-up）

短期不刪、stub 維持 sync-engine 對齊。

---

## 2026-04-29 — Generation v1.1 + Quality v1.1（採用閉環行為層補完）

**主題：對話端 trace fenced JSON convention + 即時回饋（配 PR #367 CLI 強制）**

### 動機

PR #367（CodeX、merged 2026-04-29）落地 `_meta.trace_required_statuses + save exit 1 + adoption-stats CLI + save-with-trace-from-stdin`。CLI 行為層 gate 上線後、Claude 對話層需配套 — 否則下次 `存檔` 動作會撞 exit 1、Claude 卻不知道輸出 trace fenced JSON 的 convention。

更深層：v1.5 補注（`docs/references/skill-architecture-principles.md`）揭露 trace 採用率 0/61、verifier_scores 0/61。不是「規則寫了 ≠ 行為改了」、是**價值-成本不對稱** — Claude 承擔寫 trace 成本、Kai 看不到當下價值、雙端都沒驅動力。即時回饋段是這層的解、把「未來累積分析價值」變「當下視覺價值」。

### 變更

**Generation v1.0 → v1.1**：§Output Contract 改 3 階段
1. 對話端 trace fenced JSON（Claude 必先在對話中輸出 mode / version_chosen / title_type / hook_type / verifier_prediction / brand_loaded / decisions）
2. CLI 寫入（路徑 A：`save-with-trace-from-stdin` 抽 stdin、路徑 B：手寫 `--trace`）
3. 即時回饋（save 成功後印「本支 vs 近 30 支對照」）

**Quality v1.0 → v1.1**：§Output Contract 改 2 階段
1. CLI 寫入（`record-verifier-scores`）
2. 即時回饋（印「本支 vs 同 hook_type 過去平均」+ 異常標註）

### 驗證

- rules-lint 綠（不動 valid_skills 結構、SKILL.md frontmatter 仍合 schema）
- 後續 `存檔` 流程跑、確認 Claude 自然輸出 fenced JSON + 即時回饋
- 7-14 天後跑 `adoption-stats`、若 trace 仍 0% = 假設錯、回 plan

### 不在本變更範圍

- CLI 強制 / adoption-stats CLI / `_meta.trace_required_statuses`（Codex 領土、PR #367 已落地）
- 其他 skill 變動（discovery / orientation / distillation 不動、orientation/distillation 第二輪退役另案）

---

## 2026-04-25 — Phase 5 真退役 Wave A（Claude 領土、配對 Codex Wave B）

**主題：12 個 stub-redirect skill 整刪、剩 5 核心 + harden + skill-creator**

### 退役清單（12 個目錄整刪）

| Skill | 原版本 | 落點 |
|-------|-------|------|
| flow-operator | v2.0 | Generation mode=dual-track（已內化）|
| flow-maximizer | v2.0 | Generation mode=variant（已內化）|
| series-engine | v2.0 | Generation mode=series（已內化）|
| interview-navigator | v2.0 | Generation mode=interview（已內化）|
| viral-knowledge | v2.0 | Generation mode=viral（已內化）|
| humanizer | v2.0 | Quality phase=fix（已內化）|
| script-verifier | v2.0 | Quality phase=check（已內化）|
| hook-killer | v3.0 | shared-references/templates/hook-templates.md（已降級）|
| title-generator | v3.0 | shared-references/title-rules.md（已降級）|
| topic-researcher | v1.10 | scripts/tools/research.py（待 Wave C 真實作）|
| trend-adapter | v1.20 | scripts/tools/trend.py（待 Wave C 真實作）|
| topic-architect | v2.0 | Discovery 主體（已內化）|

### 副作用

- `.claude/skills/<name>.md` 12 個 stub 同步整刪
- `02-skill-factory/README.md` v5.0 → v6.0（移 stub 對照表）
- `engine-manifest.json` 移除 12 個 contract_files SKILL.md + 對應 internal_files 子檔
- 系統 CHANGELOG v5.42 entry

### Codex Wave B（配對 PR 待補）

`scripts/lint/canonical-registry.json` valid_skills 19→7、`scripts/libs/brain_loader.py` LEGACY_SKILLS 14→2、`scripts/utils/check-version-sync.py` EXPECTED_SKILL_COUNT 19→7、`scripts/lint/rules-lint.py` 移除 vNext stub allowlist、相關 tests 同步。

### 為何不留 stub redirect

Kai 指示「新架構沒有就不顯示」。stub redirect 屬「過渡形態」、Phase 4 已給夠時間（v5.39 落地、v5.40 配對、v5.41 主 README 同步）讓員工 / 文件適應 vNext 5 核心 skill 名字。Phase 5 收乾、不再保留歷史包袱、未來員工 / 新客戶 fork 看到的就是純粹 7 個 skill。

---

## 2026-04-25 — Adoption Loop SKILL.md 端接力（Claude 領土、PR #281/#283 配對）

**主題：解 0/38 generation_trace 黑洞的 SKILL.md 端、把採用閉環從契約落地到生成行為**

### 背景

2026-04-24 Opus 4.7 視角架構判讀 + live probe：`generation_trace` 0/38、`verifier_scores` 0/38。skill-io-schema.md v1.4 §Learning Loop Contract 契約已就緒（PR #281 + #283 解 CLI 端：`set-trace` / `save --trace` / `record-verifier-scores` 完整可用）、但 skill 跑完沒結構化把 metadata 傳出 → CLI 沒被呼叫 → 0/38 持續。

球一直在 Claude 領土（`02-skill-factory/`）— 本輪一次性把 6 個生成 / 驗證 skill 的 SKILL.md 加 §Output Contract 段落、要求每次生成在輸出末尾附 fenced JSON block、Kai/Claude 可機械抽欄位呼叫 CLI。

### 6 skill SKILL.md 變更

| skill | 版本 | 變更 |
|-------|------|------|
| `script-verifier` | 1.14 → **1.15**（前輪已升、本輪只補 README/stub 漂移）| §Output Contract 指向 `record-verifier-scores` CLI、verifier 報告末尾強制附 verifier_scores JSON block |
| `flow-operator` | 1.44 → **1.50**（前輪 Opus 4.7 de-recipe 已升、本輪不動）| §Output Contract 指向 `save --trace` / `set-trace` CLI、輸出格式末尾附 generation_trace JSON block |
| `flow-maximizer` | 1.54 → **1.55** | 新增 §Output Contract、變體選定後存檔時附 generation_trace（version_chosen = V1-V5 變體編號） |
| `series-engine` | 1.35 → **1.36** | 新增 §Output Contract、**每一集**末尾附獨立 generation_trace（episode_number 為 optional extension） |
| `interview-navigator` | 1.35 → **1.36** | 新增 §Output Contract、對話腳本末尾附 generation_trace（version_chosen = 30s/45s/60s + blood_bag_score 為 optional extension） |
| `viral-knowledge` | 1.22 → **1.23** | 新增 §Output Contract、知識型腳本末尾附 generation_trace（version_chosen = A式/B式 反直覺句式、persona_deviation_score / lessons_referenced 不適用、可省略） |

### 副作用

- `02-skill-factory/README.md` 工具清單表 5 個版本同步（script-verifier 1.14→1.15、flow-maximizer 1.54→1.55、series-engine 1.35→1.36、interview-navigator 1.35→1.36、viral-knowledge 1.22→1.23）+ 用途欄補「輸出契約」標記
- `02-skill-factory/README.md` 整體版本 v4.9 → v4.10

### 已知漂移（本 PR 未修、Kai 需手動補）

`.claude/skills/` 4 個 stub frontmatter description 仍標舊版本（flow-maximizer v1.54 / series-engine v1.35 / interview-navigator v1.35 / viral-knowledge v1.22）。本 PR 試圖一併同步、被 `.claude/` 路徑 deny 攔截（permissions.md v7.0、CLAUDE.md 受保護路徑）。Kai 在 PR review 時可手動編輯 stub、或 UI 授權後請 Claude 補一個 follow-up commit。stub description 不影響 skill 運作、只影響 description 顯示一致性。

### 待 Codex 接力

1. **`docs/contracts/skill-io-schema.md` §Machine-readable Contract YAML 同步**（共享路徑、Codex 輪、待本輪 Claude PR merge 後 Codex 一次補 5 個 skills 區塊版本：flow-maximizer 1.54→1.55、series-engine 1.35→1.36、interview-navigator 不在原 YAML 需新增、viral-knowledge 不在原 YAML 需新增、script-verifier 1.14→1.15）
2. **`scripts/lint/skill-io-lint.py` 加 §Output Contract 存在性檢查**（generation skill 必含 §Output Contract section + 提及 save --trace / set-trace；script-verifier 必含 §Output Contract + 提及 record-verifier-scores）— 防未來 skill 編輯刪掉採用閉環規則、把對話內提示升級為 lint 硬規則

### 為何不一次同步 skill-io-schema.md YAML

skill-io-schema.md 是 `docs/contracts/` 共享路徑、§9.3 單向輪替。本輪 Claude 已動 6 個 SKILL.md（Claude 領土）+ README + 4 stubs（半受保護）；同 PR 再動共享契約檔會超過 §9.3 轉換邊界。Codex 該檔自然輪、配套 lint rule 一起做。

### 預期效益

- generation_trace 寫入：0/38 → 100% on new VIDs（pipeline + quick-shot 雙路線）
- verifier_scores 寫入：0/38 → 100% on new VIDs
- performance-patterns 計算可用真實 trace data、不再靠 inference
- 已上線 38 支舊影片仍合法狀態（contract 不 retroactive、見 skill-io-schema.md §Learning Loop Contract §本契約的局限）

---

## 2026-04-22 — Orchestrator Phase 3（Claude 側）

**主題：brain-loading 中央契約 + 6 skill stage 0 收斂**

### 新檔
- `shared-references/brain-loading.md` v1.0 — 統一 6 個生成類 skill 的大腦載入規範、對齊 Codex `scripts/libs/brain_loader.py`

### 6 個 skill SKILL.md 加 pointer
brain-interface / flow-operator / humanizer / flow-maximizer / interview-navigator / series-engine
每個 stage 0 段落加一行：「依 `shared-references/brain-loading.md` v1.0、透過 `brain_loader.load_for_skill()` 取得 BrainBundle」

### 解的問題
之前各 skill stage 0 分散寫載入清單、任何規則變更需 N 處同步、容易漂移（/scan 抓到、PR ef28413 修過一次）。Phase 3 建中央契約 + one-liner pointer、未來規則變更只動一處。

### 版本（本輪 skill 不升版、僅 last_updated）
- SKILL.md 內容擴充（加 pointer）、不改語意、frontmatter version 保留

---

## 2026-04-22 — /scan 深掃全修（Orchestrator Phase 1、Claude 側）

**主題：建契約層 + Hit 後置檢查點 + 大腦漂移自偵**

對應 `/scan` 第 4 階段整合報告「最高 leverage 的一個改動：Hardening Orchestrator」的 Claude 側落地。

### flow-operator v1.39 → v1.40
- 新增 §步驟 12.5「Hit 後置檢查點」：生成完成後強制產出「載入 lesson 清單 + hit 決策網格」、Kai 一鍵勾選、消滅「載入≠使用」的認知負荷
- 對應 `docs/contracts/skill-io-schema.md` v0.1 的 output spec（Hit 決策網格列為必要 section）
- 過渡設計：讓 lesson feedback loop 先跑起來、Codex 後續建 Hardening Orchestrator 時自動化

### brain-interface v1.22 → v2.2（追補對齊紀錄、commit ef28413）
- SKILL.md frontmatter + header 對齊本檔已記錄的 v2.0→v2.1→v2.2
- 下游 flow-operator:279 / flow-maximizer variant-template:92 引用「brain-interface v2.2（唯一真相源）」
- 表格 `data/skill-memory/claude-mistakes.json` → `data/[operator]/lessons.json`（engine v4.36 合併後漂移修復）

### stage 0 載入規則遷移（commit ef28413、同批次補記錄）
- 4 個生成 skill 的 stage 0 載入清單：`data/skill-memory/generation-rules.json` → `data/[operator]/lessons.json`
- 含：humanizer / flow-maximizer / interview-navigator / series-engine
- humanizer 並同步更新自我進化機制段落（3 處舊檔引用）
- 每處改用 flow-operator v1.39 template：載入過濾 `stage ∈ {candidate, active}` + scope 匹配 + counter_pattern/pattern 雙欄位

### 02-skill-factory/README.md 對齊
- flow-operator v1.37 → v1.39（對齊 SKILL.md）
- brain-interface v1.22 → v2.2（對齊本 CHANGELOG）
- 最後更新日期 2026-04-17 → 2026-04-22

### 共享契約新增（docs/contracts/）
- **skill-io-schema.md v0.1**：定義 6 個核心 skill 的 IO 契約、Codex 後續寫 `scripts/lint/skill-io-lint.py` 以此為 SSoT
- **hardening-queue-schema.md v0.1**：Orchestrator queue 契約、6 種 proposal type、Claude 消費 × Codex 建 queue 雙向對齊（**v4.67 Stage F 整層退役 + 本檔刪除**、因實證 0 proposal 被產出、改由 `/harden` 對話內 skill 承擔、見 CHANGELOG v4.67）

### 根因（為何這波一次做）

`/scan` 三層深掃（大腦 / 引擎 / 學習）× 雙代理（Claude / Codex）= 6 份獨立報告、指向同一主根因：
> **系統會累積規則、但不會自動執行規則。**

本輪 Claude 側先落地：skill 自身（版本對齊 + Hit 網格）+ 契約文檔（IO + queue）。Codex 側 Phase 1-2（brain_loader / CLI 驗證器 / Orchestrator MVP）依契約後續實作。

---

## 2026-04-17 — 第二輪優化（內容瘦身）

**主題：去重、砍死碼、版本紀錄集中化**

### 結構變動

- **刪除各 skill 內的「版本紀錄」表格章節（15 skills）**
  每個 skill 原本尾端有 ~7 行的 per-skill 版本表格，已統一由本檔案承接。
  各 skill 留下 `<!-- 版本歷史見 02-skill-factory/CHANGELOG.md -->` 指標。

- **刪除過時的「vN.XX 升級紀要」章節（5 skills）**
  hook-killer (v1.11)、series-engine (v1.31)、flow-maximizer (v1.51)、
  script-verifier (v1.12)、title-generator (v1.11) — 原本寫在檔頭的舊版升級筆記，
  內容已被數次 refactor 覆蓋，維持只會誤導讀者。

### 行數變化

| skill | before | after | Δ |
|-------|-------:|------:|---:|
| brain-interface | 43 | 35 | -8 |
| daily-raw-to-inbox-lite | 155 | 144 | -11 |
| flow-maximizer | 260 | 241 | -19 |
| flow-operator | 308 | 294 | -14 |
| hook-killer | 230 | 213 | -17 |
| humanizer | 108 | 101 | -7 |
| interview-navigator | 411 | 399 | -12 |
| publish-optimizer | 161 | 155 | -6 |
| script-verifier | 212 | 197 | -15 |
| series-engine | 311 | 293 | -18 |
| title-generator | 145 | 131 | -14 |
| topic-architect | 368 | 356 | -12 |
| topic-researcher | 326 | 315 | -11 |
| trend-adapter | 253 | 243 | -10 |
| viral-knowledge | 302 | 291 | -11 |
| **合計** | **3593** | **3408** | **-185** |

skill-creator（官方 MCP skill）未動。

### 未執行（audit 提出但評估後跳過）

| 項目 | 原因 |
|------|------|
| 搬走 skill-creator | 官方 MCP 內建 skill，動不得 |
| 砍 Gotchas 章節 | Gotchas 是錯誤記憶載體，即使看似「多餘」也要留 |
| 統一中文 / 英文 SKILL 標題 | 純風格，無功能差異；風險大於收益 |
| 收攏 script-verifier quality-gates 重複 | audit 誤判：實際已是引用形式（`見 quality-gates.md`），非重複 |
| 改 topic-architect v1.21↔v1.22「衝突」 | audit 誤判：frontmatter 正確為 v1.22，header 是舊標記 |

---

## 2026-04-17 — 全修批次（skill-creator 審查）

**主題：結構健康度對齊、description 具體化、evals 覆蓋率補齊**

### brain-interface v2.1 → v2.2
- frontmatter description 由「數據大腦接口規格 — 定義 Skills 如何讀取品牌知識」（VAGUE）
  改為「需要查看接口規格、模組欄位定義、或除錯 Skill 讀取問題時觸發」（CONCRETE）
- stub 對齊

### topic-architect v1.21 → v1.22
- 補觸發詞「萃取選題」「用 topic-architect」
- 明示與 topic-researcher `[外部研究]` 邊界：architect 只讀內部大腦，researcher 走 Google/Dcard/PTT
- stub 對齊

### humanizer v1.23 → v1.24
- SKILL.md 525 → 108 行（-79%）
- 抽 `references/ai-patterns.md`（24 patterns + 中文適用性）— **後 v4.8 Phase 3a 重新內聯回 SKILL.md、refs 檔已刪**
- 抽 `references/voice-and-soul.md`（voice 思路 + 完整範例）— **後 v4.8 Phase 3a 重新內聯回 SKILL.md、refs 檔已刪**
- 按需載入降低常駐 context

### 補 evals（7 → 11，覆蓋率 44% → 69%）
- hook-killer：`evals/eval-hook-generation.md`（7 測試案例）
- title-generator：`evals/eval-title-generation.md`（6 測試案例）
- publish-optimizer：`evals/eval-publish-brief.md`（6 測試案例）
- script-verifier：`evals/eval-five-checks.md`（9 測試案例，含虛構攔截紅線）

---

## 2026-04-15 — 版本號清理

- flow-maximizer v1.51 → v1.52
- hook-killer description 版本 v1.11 → v1.14（對齊 frontmatter）
- script-verifier description 版本 v1.11 → v1.14（對齊 frontmatter）
- series-engine description 版本 v1.31 → v1.32（對齊 frontmatter）
- title-generator description 版本 v1.11 → v1.14（對齊 frontmatter）

---

## 2026-04-14 — 發布流程延伸 + 多項升版

- publish-optimizer v1.0 新建（發布簡報 4 項）
- brain-interface v2.0 → v2.1（補版本紀錄）
- topic-architect v1.2 → v1.21
- topic-researcher v1.4 → v1.5（三合一：深挖 + 靈感 + 輿情）
- title-generator v1.1 → v1.14（對齊 workflow.md ②）

---

## 2026-04-10 — humanizer 品牌人格注入

- humanizer v1.22 → v1.23（兩階段：掃描 + 人格注入）

---

## 2026-04-07 — brand.md / cases.md 架構對齊

- 全 skill 加註「brain-refs: updated 2026-04-07 for brand.md/cases.md architecture」
- brain-interface v2.0（對齊新架構）

---

## 2026-04-05 — script-verifier 成為唯一品管關卡

- script-verifier v1.12 → v1.14（合併 Soft Gates 的數據一致性 + 虛構攔截）

---

## 2026-04-03 — trend-adapter 雙模式

- trend-adapter v2.0（自動 / 手動+截圖 雙模式）

---

## 2026-03-26 — 多個 skill 同步升版

- flow-maximizer v1.5 → v1.52（角度變體器穩定版）
- hook-killer v1.1 → v1.14
- interview-navigator v1.3 → v1.32
- series-engine v1.3 → v1.32
- viral-knowledge v1.2 → v1.22

---

## 維護原則

1. **per-skill 版本紀錄集中此檔**，不在各 SKILL.md 尾部重複
2. **version 欄位連動**：SKILL.md frontmatter + stub + 此檔同步
3. **新增條目時機**：
   - frontmatter description 修改 → 必記
   - 結構重組（拆 references / 改 process）→ 必記
   - 新增 evals → 必記
   - 純字詞調整（typo / 格式）→ 可省略
4. **分類標記**（可選）：🔧 結構 / 📝 description / ✅ evals / 🎯 process

### 與系統 CHANGELOG 關係

- `07-changelog/CHANGELOG.md` = 系統級（CLAUDE.md / workflow.md / 跨 skill 治理）
- 本檔 = skill 內部版本演進
- 大型里程碑兩邊都記（例：「全修批次」系統 CHANGELOG 只寫 1 行指向本檔）
