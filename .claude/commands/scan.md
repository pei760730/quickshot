# /scan — 責任區掃描

讀取 `docs/contracts/agent-collaboration.md` 完整協議，依 Claude 責任區執行掃描。

## 執行步驟

1. 讀取 `docs/contracts/agent-collaboration.md`
2. 依協議 Section 1 確認自己的責任區
3. **並行掃描責任區子樹**：每個資料夾派一個 `Explore` subagent（`.claude/**`、`02-skill-factory/**`、`01-data-brain/**`、`03-production-line/**`、`07-changelog/**`、`00-control-center/**`），一次 dispatch 多個。主 agent 只做收斂與 Top3 排序，子 agent 的 context 不污染主對話
4. 依協議 Section 7 產出報告（必含：Top3 + 同步委託段）

## 變體

- `/scan` — 只產出報告，不改動
- `/scan full-fix` — 產出報告後直接執行全部修改（依協議「全修執行規則」段落）

## 格式守門

兩項必產出（見協議 Section 7）：
- **Top3**（每項含 Owner + Blocking）
- **同步委託段**（✂️ 可複製貼給對方代理，觸發雙方閉環）
