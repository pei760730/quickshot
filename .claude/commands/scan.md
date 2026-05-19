# /scan — 責任區掃描

對 quickshot template 做一輪深度掃描、找出系統級問題：壞掉的自動化 / 死引用 / 規則漂移 / 文件與實作斷裂 / lint 缺口。

> KaiOS 雙 agent 協作的 `agent-collaboration.md`「責任區 / 同步委託段 / Owner 分流」已隨 README §砍掉的 3 大模組退役、本 template 單 Claude agent 不適用。

## 執行步驟

1. **並行掃描子樹**：派 `Explore` subagent 平行掃以下目錄、一次 dispatch 多個。主 agent 只做收斂 + Top3 排序、子 agent 的 context 不污染主對話：
   - `.claude/**`（hooks / rules / commands / skills / settings）
   - `02-skill-factory/**`（skills + shared-references + CHANGELOG）
   - `01-data-brain/**`（brand / cases / personas / transcripts）
   - `03-production-line/**`（ready-to-shoot / done）
   - `07-changelog/**`（CHANGELOG 索引一致性）
   - `scripts/**` + `tests/**`（CLI / lint / 測試）
   - `docs/contracts/**` + `docs/references/**`

2. **收斂 Top 3 報告**：每項包含
   - **問題**：什麼壞 / 漂移 / 矛盾
   - **證據**：具體 `file:line`
   - **修法**：能不能用 lint / 規則 / 文件擋住（CLAUDE.md 禁令 #6「硬化優先」三層）
   - **風險**：受不受 `.claude/settings.json` deny list 保護、改動範圍

3. **依風險分層列剩餘 Issues**：High / Medium / Low、每層含具體檔位與建議修法。

## 變體

- `/scan` — 只產出報告、不改動
- `/scan full-fix` — 報告後直接執行所有低風險修改；受保護路徑（`CLAUDE.md` / `.claude/**`）仍需 Kai 確認

## 格式守門

兩項必產出：
- **Top 3**（問題 + 證據 + 修法 + 風險）
- **Recommended next actions**（依優先順序列、含「需要 Kai 解 deny lock 的項目」獨立段）
