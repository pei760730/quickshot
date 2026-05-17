# 系統設計原則 — 追溯與本地化

> version: 1.1 | created: 2026-04-21 | last_updated: 2026-05-15
> 記錄本系統中哪些原則來自外部（主要為 Boris Cherny / Claude Code 團隊），哪些是本專案原創改造。避免內部引用變成確認偏誤。

## 為什麼有這個檔

當 Kai 或 Claude 在系統中引用「Boris 說」「Ryan 說」時、應該指得出來源。沒來源的「原話引用」會讓規則體系失去可驗證性——未來被外人指出錯誤時、整套論述會動搖。本檔為所有關鍵原則建立 audit trail。

每次吸收新的外部觀點 → 新增一節；每次原創一個超出外部的機制 → 新增到「本專案原創」；每季盤點「外部原則」本地是否已變形到不認得、可能該升為「本專案原創」。

---

## 外部原則 — 來自 Boris Cherny / Claude Code 團隊

### Plan mode（`CLAUDE.md §3.5`）
- 來源：Boris 官方 CLAUDE.md（github.com/0xquinto/bcherny-claude）L53-58 + 2026-01 X thread
- 原話：「Start every complex task in plan mode... When something goes sideways, switch back to plan mode and re-plan. Don't keep pushing.」
- 本地化：觸發條件具體到「多檔連動 ≥ 3、全修指令、卡住重回」。比 Boris 更結構化、核心「預先規劃 + 走不通重走」不變。

### Headless Claude（已退役、v4.69）
- 來源：Boris 2026-03 thread Tip #3 + Latent Space podcast
- 本地化嘗試：Boris 用於 CI 輔助 / 批次重構；本專案原限定「上游蒐集 + 下游提醒」、生產決策永遠人在環
- **退役原因（v4.69）**：規格寫了 2 個月、3 個 task workflow 從未實作、Kai 實際工作都在對話中、headless cron 路徑對本專案無價值。契約 `docs/contracts/headless-tasks.md` + 相關 workflow 全刪。留此條當「試過、不適合」的脈絡記錄。

### Verification loops（`script-verifier` skill）
- 來源：Boris 2026-04 Opus 4.7 thread Tip #6 + 官方 CLAUDE.md
- 原話（轉述）：「Give Claude a way to verify its own work for 2-3x quality improvement」
- 本地化：驗證結果回報 Kai、由 Kai 決定是否重寫。不自動重寫（對應「人在環」原則）。

### 錯誤沉澱 / 自我進化（`lessons.json` + workflow.md 進化提案）
- 來源：Boris 官方 CLAUDE.md L45-51「After every correction or mistake, update this CLAUDE.md with a rule... Claude is good at writing rules for itself.」
- 本地化（v4.7 後）：Boris 用單檔 CLAUDE.md 直接改；本專案用 3 態 lessons（soft → hardened → archived）+ 硬化路徑（test / lint / claude_md / workflow_md / brand_md）對照表 + `/harden` 對話內 skill。結構化比 Boris 多一層、但核心「讓 Claude 自己寫規則給自己」一致。**v4.7 前曾有 5 態 + hit_count + hardening_status、Stage C v4.63 降維、見 CHANGELOG**。

### Hook 分工哲學（`.claude/settings.json`）
- 來源：Boris 2026-03 thread Tip #4
- 原則：deterministic（log、format、permission 分流、SessionStart 注入）交給 hook；語意判斷才丟 LLM。

### Context 管理 / `/compact` with hint（`CLAUDE.md` 操作原則）
- 來源：Latent Space podcast 轉述（vlad.build 筆記）
- 原話（轉述）：「Model is at its least intelligent point when auto-compacting due to context rot」
- 本地化：> 60% 提醒時主動建議 `/compact <hint>`、不等 autocompact。

### Git worktree（`docs/references/worktree-guide.md`）
- 來源：Boris 2026-03 thread + worktree 最佳實踐
- 本地化：用於平行工作區、避免分支切換清狀態。

---

## 本專案原創 — 超出 Boris 範疇

### `lessons.json` 3 態（v4.63+ soft / hardened / archived）
Boris 用單檔 CLAUDE.md、記錯即改。本專案因短影音生產週期長 + 多 operator、設計 `soft → hardened` 升級機制 + 5 種硬化路徑對照表（見 `docs/contracts/lessons-schema.md` v2.3）。v4.7 前的 5 階段 + hit_count 觀測設計於 Stage C 降維、見 CHANGELOG v4.63。

### `brand.md` 為品牌 SSoT（v4.62+ lazy load、全文注入退役）
brand.md 從 v4.62 改 lazy load：skill 跑時 `scripts/libs/brain_loader.py` 自動載入、對話需要時 Claude 主動 `Read 01-data-brain/brand.md`、SessionStart hook 不再 cat 全文（每 session 省 ~27k token baseline）。v4.7 前曾有 `brand-summary.md` 衍生速查檔 + 鏈式同步、Stage A 廢除（Opus 4.7 可吃全文、衍生層只帶來漂移成本）、見 CHANGELOG v4.62。

### `pipeline.json` 為狀態 SSoT + `_meta.thresholds`
Boris 不做生產流程管理。本專案的狀態機、門檻定義、Sheets 同步都圍繞此 SSoT。

### `data/.operators.json` 動態 operator 清單（v4.38+）
多 operator 架構、一 repo 可服務多品牌。Boris 原版單人使用。

### 三層硬化判斷（`CLAUDE.md §7`）
「修 bug / 加 feature 前自問：(a) lint/test 擋得住嗎 (b) 規則文字寫得清嗎 (c) schema 欄位約束得了嗎」。Boris 沒明確提出此三層分類。

---

## 誠實披露 — 非原話的濃縮

### 「代碼免費、prompt + guardrail 才是王道」（`CLAUDE.md §7` 背景句）
目前以「Ryan 的」為引。研究未找到 Boris 或 Ryan 的公開原話。這是對 Boris 多篇訪談觀點的第一性原理濃縮：

- 「agents write the code you allow them to write」（InfoQ 2026-01 轉述）
- 「80-90% of the code used in Claude Code is written by Claude itself」（Latent Space）
- 「prune as much as they build」（Every podcast）

對外引用時應說「本系統對 Boris Cherny 多篇觀點的整理」而非「Boris 原話」。
