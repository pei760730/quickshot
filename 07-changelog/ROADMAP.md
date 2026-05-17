# 未來優化路線圖（ROADMAP）

> 紀錄已知可優化的方向。完成後打勾並註明在哪個版本解決。

---

## 🔴 高優先（影響日常使用）

- [x] **數據大腦持續補充** — ✅ 2026-03-06 全模組已填（v3.5 大幅補充 Q22~Q33）

## 🟡 中優先（功能擴展）

- [ ] **Ann 用 Sheets 丟靈感** — Ann 在 Google Sheets 填靈感 → 自動同步到 `data/{operator}/pipeline.json` 的 `items[]`（status=inbox；v3.x 後靈感與影片統一管線、原規劃的 `idea-tracking.json` 獨立檔從未實作）
- [ ] **N8N 自動化流程** — 串接 N8N Cloud，腳本通過質檢/內容上線等事件自動觸發通知
- [x] **掃描時間判斷優化** — ✅ 2026-04-11 pipeline.json 為 SSoT（含 status_history/created_date/publish_date），不再依賴檔案名稱日期

## 🟢 低優先（錦上添花）

- [x] **素材庫填充** — ✅ 2026-03-04 已建立 413 行素材（開場/CTA/標題）；2026-03-27 SSoT 遷移至 performance-patterns.json，04-asset-library 降級為唯讀歸檔
- [x] **素材庫自動盤點** — ✅ 2026-03-27 已由 performance-patterns.json 自動管理（Skill 生成時自動注入）
- [ ] **腳本版本對比** — 同一選題的 V1/V2/V3 之間的差異摘要

---

## ✅ 已完成

| 項目 | 完成版本 | 日期 |
|------|----------|------|
| 多人協作機制（角色權限） | v2.0 | 2026-02-07 |
| 動態掃描取代靜態模板 | v2.0 | 2026-02-07 |
| system-logs 改為單檔月誌 | v2.0 | 2026-02-07 |
| 系統變更追蹤機制 | v2.0 | 2026-02-07 |
| Google Sheets 五分頁儀表板 | v3.0 | 2026-02-19 |
| 週報/月報自動填數字（Sheets 報表） | v3.0 | 2026-02-19 |
| 月報匯總（週報+月報+靈感轉化合併） | v3.0 | 2026-02-19 |
| Crew日報系統（analyze/fetch/archive） | v3.3 | 2026-02-21 |
| 數據回填截圖法（IG 截圖 → 自動計算） | v3.3 | 2026-02-21 |
| 影片追蹤（7 欄 Sheets 分頁） | v3.3 | 2026-02-21 |
| 生產線 3 階段重構 | v3.3 | 2026-02-21 |
| Hard Gates 強制化 | v3.4 | 2026-03-01 |
| CLAUDE.md 瘦身（280→130 行，按需載入） | v3.4 | 2026-03-01 |
| 週五 HG-FAIL 快速統計 → Skill 升版提議 | v3.4 | 2026-03-01 |
| today.md 雙軌更新（Hook + Claude）| v3.4 | 2026-03-01 |
| GitHub Actions push 觸發自動 sync | v4.0 | 2026-03-04 |
| 死碼大清掃（~1,500 行刪除） | v4.0 | 2026-03-04 |
| sync-to-sheets.py v4.0 重構 | v4.0 | 2026-03-04 |
| 數據回填提醒機制（交付後 3 天自動列🟡） | v4.0 | 2026-03-04 |
| 治理架構去團隊化 | v4.1 | 2026-03-20 |
| 7 Skill 統一優化 + 版本號統一 v1.XX | v4.2 | 2026-03-27 |
| risk_patterns 建立（4 條負面學習） | v4.2 | 2026-03-27 |
| 學習覆蓋率 36%→100%（28/28） | v4.2 | 2026-03-27 |
| 錯誤記憶系統 claude-mistakes.json | v4.2 | 2026-03-27 |
| 存檔 manifest 3→4 步（Skill 記憶寫入） | v4.2 | 2026-03-27 |
| 腳本統一放 kai/ 子目錄 | v4.2 | 2026-03-27 |
| lint 0 warnings + validate-all 0 warnings | v4.2 | 2026-03-27 |
| 04-asset-library 降級為唯讀歸檔 | v4.2 | 2026-03-27 |
| patterns.md 遷移至 claude-mistakes.json | v4.2 | 2026-03-27 |
| CLAUDE.md v4.0 + workflow.md 獨立拆出 | v4.3 | 2026-04-14 |
| workflow-analytics.md 獨立拆出 | v4.3 | 2026-04-14 |
| docs/contracts/ 契約系統（6 份） | v4.3 | 2026-04-14 |
| 品質體系重構（quality-gates v2.0 + 4 子文件） | v4.3 | 2026-04-14 |
| topic-researcher Skill 新建（v2.1） | v4.3 | 2026-04-14 |
| trend-adapter Skill 新建（v2.0） | v4.3 | 2026-04-14 |
| 4 Skill 升版（script-verifier/title-generator/humanizer/brain-interface） | v4.3 | 2026-04-14 |
| 掃描機制建立（agent-collaboration + /scan） | v4.3 | 2026-04-14 |
| Skill 索引修復 + 版本號三層統一 | v4.3 | 2026-04-14 |
| data-brain-manifest 漂移偵測重構（零維護） | v4.3 | 2026-04-14 |
| 回填即洞察（workflow-analytics v3.0） | v4.4 | 2026-04-14 |
| publish-optimizer Skill 新建（v1.0） | v4.4 | 2026-04-14 |
| 贏家複製（winner-replicator） | v4.4 | 2026-04-14 |
| CLAUDE.md 禁令 #4#5（精準修改 + 改動自驗） | v4.5 | 2026-04-15 |
| Opus 4.7 Phase 1：flow-operator 子檔合併（10→3） | v4.6 | 2026-04-18 |
| Opus 4.7 Phase 1：quality-gates pipeline 並行化 | v4.6 | 2026-04-18 |
| Opus 4.7 Phase 1：agent-collaboration 5 段格式精煉 | v4.6 | 2026-04-18 |
| Opus 4.7 Phase 2：CLAUDE.md 禁令 #3 三層判斷 | v4.7 | 2026-04-18 |
| Opus 4.7 Phase 2：path-guard.sh 換原生 permissions | v4.7 | 2026-04-18 |
| Opus 4.7 Phase 2：workflow 加 TodoWrite 追蹤 | v4.7 | 2026-04-18 |
| Opus 4.7 Phase 2：/scan 並行 Explore subagent | v4.7 | 2026-04-18 |
| Opus 4.7 Phase 3a：4 個 skill references 瘦身（-1594 行） | v4.8 | 2026-04-18 |
| Opus 4.7 Phase 3c：Codex Python 防呆清理（backfill hot path + validate 重構 + renumber 簡化） | v4.9 | 2026-04-18 |
| Opus 4.7 Phase 4a：客戶生命週期工具組（bootstrap + sync-engine + template） | v4.9 | 2026-04-18 |
| Opus 4.7 Phase 4b：brand-summary SessionStart 注入 | v4.10 | 2026-04-18 |
| Opus 4.7 Phase 4b：CLAUDE.local.md 分離（客戶身份不被 sync-engine 覆蓋） | v4.10 | 2026-04-18 |
| Opus 4.7 Phase 4b：client-lifecycle.md 補類型 2 客戶流程 | v4.10 | 2026-04-18 |
| Opus 4.7 Phase 4b：auto_extract parse cache + pipeline _validate_for_save 抽取 | v4.10 | 2026-04-18 |
| test_brand operator-agnostic（bootstrap 不再誤 break test） | v4.10 | 2026-04-18 |

---

## 🗺️ 下一階段候選（2026-04-19+）

### 中優先

- [x] **Phase 3d：契約語氣正向化** — ✅ v4.11 / 2026-04-18 red-line-protocol.md v1.0 → v2.0（每條紅線「正向原則 + 對照避免行為」雙欄）
- [x] **16 個 stub description 語意化重寫** — ✅ v4.11 / 2026-04-18（Opus 4.7 語意觸發優化、現為 17 個 stub）
- [ ] **Codex sandbox 一勞永逸配置** — Codex Cloud 平台 init script + GitHub token secret，讓 Codex 能自己 push / close PR
- [ ] **接長兄 OS 實戰** — 走一遍 Phase 4a + 4b 客戶 lifecycle 流程實測

### 低優先

- [ ] **Codex Round 3 Top3 補交** — sedimentation.py 用 Counter + groupby 重寫（Codex 上輪欠的）
- [ ] **Anthropic Python SDK 遷移** — skill-creator/scripts/improve_description.py 從 subprocess 改 SDK（支援 prompt caching）
- [ ] **KaiOS-Engine public 子 repo** — 類型 2 客戶（Gmail 帳號）的長期最優解，讓 A private 但引擎 public
- [ ] **腳本版本對比** — 同一選題的 V1/V2/V3 差異摘要
- [ ] **Ann 用 Sheets 丟靈感** — Sheets 自動同步到 pipeline.json inbox
- [ ] **N8N 自動化流程** — 事件觸發通知
