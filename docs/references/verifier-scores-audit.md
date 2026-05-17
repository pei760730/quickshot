# record-verifier-scores audit

> 觸發：Learning-loop spec #266、live probe 0/38

## 呼叫點清單

### 直接呼叫（runtime）
- `scripts/ops/video-ops.py:1443`：`record-verifier-scores` CLI 分支把解析後 `scores` 傳入 `record_verifier_scores(data, vid, scores)`。  
- `scripts/ops/lib/pipeline.py:1017`：`record_verifier_scores()` 函式定義（實際寫入 `video["verifier_scores"]`）。

### 非呼叫點（僅提及/說明/測試）
- `scripts/ops/video-ops.py:48,1424,1426`：CLI docstring 與 usage（不是執行呼叫）。  
- `tests/test_verifier_scores.py:*`：單元測試呼叫（非 production flow）。  
- `docs/contracts/video-ops-cli.md:60`、`docs/contracts/lessons-schema.md:85,118`、`docs/references/production-details.md:29,30`：文件描述（非執行路徑）。

### 指定檢查檔案結果
- `scripts/ops/lib/backfill.py`：**0 處**呼叫 `record_verifier_scores`。  
- `scripts/ops/lib/auto_extract.py`：**0 處**呼叫 `record_verifier_scores`。  
- 其餘 glue：`scripts/ops/video-ops.py` 僅在 CLI `record-verifier-scores` 子命令中呼叫一次（見上）。

## 為什麼 0/38 live data？

結論：**目前是「有實作、但未接入日常主流程」**。  

- 目前 production path（`save`、`backfill`、`extract-learning`）都沒有自動呼叫 `record_verifier_scores`。  
- 唯一入口是手動 CLI：`video-ops.py record-verifier-scores ...`。  
- 若現場流程未明確執行該命令，就會出現 live probe `0/38`（並非函式壞掉，而是觸發點不存在/未被流程採用）。

## 建議

1. **若問題在 skill 流程未觸發**：交給 Claude 在 `script-verifier` / workflow 端補上固定呼叫節點（Claude 領土）。  
2. **若要由 CLI 端補防呆**：Codex 可另開 PR（不在本 audit）加入 `save` 後提醒或狀態檢查，提示「尚未記錄 verifier_scores」。  
3. 保持本次 audit 純文件，不修改 `record-verifier-scores` 指令本體與 skill 檔案。

