# 未來優化路線圖（ROADMAP）

> **scope：quickshot 短期客戶 template 自己的路線圖**（v7.00 fork 之後）。
> KaiOS 主引擎時期的 roadmap 項目與已完成歷史（v2.0~v4.10 引擎演進、Ann Sheets 靈感、N8N 自動化、KaiOS-Engine public 子 repo 等）已移除 —— 那些屬於 KaiOS-ContentSystem repo 的世界觀、不是本 template 的；歷史紀錄見 [CHANGELOG-archive-v4.x.md](./CHANGELOG-archive-v4.x.md) / [CHANGELOG-archive-v5.x.md](./CHANGELOG-archive-v5.x.md)（KaiOS lineage、唯讀）與 git history（改寫前版本：2026-06-10 之前）。
> 完成後打勾並註明在哪個版本 / PR 解決。

---

## 🔴 高優先（影響下一個客戶）

- [ ] **第一個真實客戶走完全生命週期** — `/init` 冷啟動 → 生產迴圈 → Day-30 驗證收尾（workflow.md v2.35 §Day-30）→ wipe 或續約交接。整套 template 至今只被 longbro 走過前半段、收尾流程從未實測。
- [ ] **Mode W 1 個月 metric 檢查（2026-07-10 到期）** — Day-30 收尾流程 + 沉澱門檻短期適配（5→2）的採用率。注意：無掛客戶期間 metric 凍結、時鐘從下一個 `/init` 起算（見 skill-architecture-principles.md v1.8.1）。

## 🟡 中優先（功能擴展）

- [ ] **Codex sandbox 一勞永逸配置** — repo 側已備（`scripts/codex/setup.sh` + `docs/references/codex-sandbox-setup.md`、2026-06-10）；剩平台側：Kai 建 fine-grained PAT 貼進 Codex Cloud secret + setup script 欄位填 `bash scripts/codex/setup.sh`、第一次派工驗證三項通過後打勾
- [ ] **續約升級 KaiOS 交接清單實測** — Day-30 收尾若判「續約」、驗證哪些繼承的治理機器（lessons / patterns / territory）真的被復用（餵 skill-architecture-principles.md v1.8.4 第四輪審視）

## 🟢 低優先（錦上添花）

- [ ] **Anthropic Python SDK 遷移** — skill-creator/scripts/improve_description.py 從 subprocess 改 SDK（支援 prompt caching）

---

## ✅ 已完成（quickshot 自己的）

| 項目 | 版本 / PR | 日期 |
|------|----------|------|
| v7.00 short-term template fork（從 KaiOS 砍出） | PR #1 | 2026-05-17 |
| longbro 客戶結束、wipe 回 template 狀態 | wipe | 2026-05-17 |
| 雙 agent 協作輕量重新引入（territory-lint CI + AGENTS.md） | PR #20–#27 | 2026-06-04 |
| 多代理重新引入後 doc-vs-reality 對齊 | PR #28 | 2026-06-05 |
| 方向心法 shared-reference + 接入 discovery / generation | PR #29–#31 | 2026-06-08 |
| 第三輪架構審視（世界觀對齊 + Day-30 收尾 + stale claims 防回歸） | 本輪 | 2026-06-10 |
| Codex Round 3 Top3 補交 — sedimentation 重複問題統計收斂為分類表 + 一趟掃描（Counter/groupby 字面方案評估後否決：groupby 需先排序、無增益） | claude/sedimentation-refactor | 2026-06-10 |
| 腳本版本對比 — 以對話準則落地（workflow.md v2.36 §腳本版本對比）、不寫 code（禁令 #9 預測不做）；真實使用不夠再升 CLI | workflow.md v2.36 | 2026-06-10 |
