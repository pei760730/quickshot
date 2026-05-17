# Codex Mental Model Sync（2026-04-23）

## 目的
- 將 KaiOS-ContentSystem engine v4.51 → v4.69 的全修同步，落地為 Codex 後續執行基線。

## 1) 失效中的 pending / in-progress 工作（立即停用）
- 任何 hardening queue 狀態機、observer trigger、executor action dispatch 擴充。
- 任何以 `pipeline.items[].skills_executed` 為寫入或分析來源的工作。
- 任何 `headless-tasks.md` 三個 cron task 的實作計畫。
- 任何 `analytics-protocol.md` 中 backfill 自動 insight / Active Sedimenter 的落地計畫。
- 任何 brand-summary 派生檔產生、同步、bootstrap/fork 清理流程。
- 任何 lessons 5 態（`observation/candidate/active/graduated/archived`）假設相關的改動。

## 2) 被推翻的心智模型假設
- `hardening-queue.json` 不是 SSoT；硬化主線改為 `/harden` 對話內流程。
- `skills_executed` 不再是 pipeline 欄位；單值 `skill_used` 才是有效來源。
- `headless-tasks.md` 不會實作，且文件已刪除。
- lessons stage 不再是 5 態；僅允許 `soft/hardened/archived`。
- hit-count 自動硬化策略退役；改為對話中主動判斷硬化時機。

## 3) 後續執行守則（立即生效）
- 硬化需求一律走 `harden_from_dialog(...)`，必要時採 protected-md 寫入模式。
- 寫入 lessons 時僅接受 3 態 stage，且不帶 `confidence`。
- skill 使用率僅以 `skill_used` 或對話紀錄查詢。
- 變更契約檔（`docs/contracts/*.md` 等 contract scope）時，務必同步版本與 engine bump；internal scope 改動不強制 bump。
- `schema_drift.py` 仍為活躍能力，契約版號未 bump 會觸發 breaking 檢查。

## 4) 下一階段建議（給 Kai）
- 建議封版觀察 2–4 週，集中追蹤 3 個生產指標：
  1. `/harden` 實際使用頻率與成功率。
  2. lessons `soft → hardened` 轉換品質（是否有誤硬化或漏硬化）。
  3. schema drift 告警噪音比（intentional-breaking 判定是否足夠穩定）。
- 觀察期內避免新增新一層 orchestration；優先修補對話內流程可觀測性與回溯性。
