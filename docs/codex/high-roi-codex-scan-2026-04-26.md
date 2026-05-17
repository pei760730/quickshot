# CodeX 高收益掃描清單（2026-04-26）

> 範圍：僅 CodeX 負責（tests / scripts / tooling），不碰 Claude 主體架構。

## 1) 收斂 `tests/test_sheets_direct.py` 的手動 `sys.path.insert`

- **現況**：`tests/test_sheets_direct.py` 仍手動 `sys.path.insert(0, str(UTILS_DIR))`。  
  已與近期建立的 `tests/path_bootstrap.py` 收斂方向不一致。
- **立即收益**：
  - 降低測試 bootstrap 規則分岔（避免之後又出現第二套 path 規則）。
  - 減少 import 問題 debug 成本（統一入口更容易追）。
- **最小動作**：
  1. 在 `tests/path_bootstrap.py` 新增 `bootstrap_utils_test_sys_path()`。
  2. 以 helper 取代 `tests/test_sheets_direct.py` 內手動 insertion。
  3. 補一個小型 regression test（驗證 helper 會把 `scripts/utils` 放到最前且去重）。

## 2) 為 subprocess 型測試補 timeout / fail-fast（優先 `tests/test_bootstrap.py`）

- **現況**：`tests/test_bootstrap.py` 多處 `subprocess.run(..., check=True)` 未設定 timeout。  
  若 CI 或環境異常，可能導致工作卡住且不易診斷。
- **立即收益**：
  - 降低 CI hanging 風險。
  - 失敗訊號更快，排障時間下降。
- **最小動作**：
  1. 為 `subprocess.run` 加 `timeout`（例如 20~30 秒）。
  2. 失敗時保留 `stdout/stderr` 到 assertion message。
  3. 跑既有 bootstrap 測試確認無行為改變。

## 3) 將 bootstrap helper 行為契約補到 docs/contracts（薄文件）

- **現況**：`tests/path_bootstrap.py` 已成為測試 import 事實標準，但尚無精簡契約文件。
- **立即收益**：
  - 新加入測試時能依單一契約執行，降低再次散落 `sys.path.insert` 的機率。
  - 減少 reviewer 對「為什麼這樣 prepend」的溝通成本。
- **最小動作**：
  1. 在 `docs/contracts/` 新增短文件（1 頁內）：說明 `PROJECT_ROOT / OPS / ENGINE` 三者用途與優先序。
  2. 明確列出「允許/禁止」做法（允許用 helper、禁止 ad-hoc insertion）。
  3. 在 `tests/path_bootstrap.py` docstring 加一行對應文件路徑。
