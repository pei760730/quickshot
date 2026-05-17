# 災難復原劇本

> version: 1.0 | created: 2026-03-20
> 用途：系統出問題時的 SOP，照做就能恢復

---

## 場景 1：JSON 檔案損壞（打不開 / 格式錯誤）

**症狀**：任何 `video-ops.py` 指令報 `JSONDecodeError` 或 `格式損壞`

**恢復步驟**：

```bash
# 1. 確認哪個檔案壞了
python scripts/ops/video-ops.py validate

# 2. 從 git 還原（最近一次正常的版本）
git checkout HEAD -- data/kai/pipeline.json
# 或
git checkout HEAD -- data/kai/performance-patterns.json

# 3. 如果 HEAD 版本也壞了（已經 commit 了損壞版本）
git log --oneline data/kai/pipeline.json  # 找到正常的 commit
git checkout <commit-hash> -- data/kai/pipeline.json

# 4. 還原後驗證
python scripts/ops/video-ops.py validate-all
```

**預防**：不要手動編輯 JSON 檔案，所有操作走 `video-ops.py`。

---

## 場景 2：多步驟操作中途失敗（上線 / 存檔 / 回填）

**症狀**：操作回報「N/3 步驟完成」或 Claude 中途斷線

**恢復步驟**：

```bash
# 1. 跑驗證，看哪裡不一致
python scripts/ops/video-ops.py validate-all

# 2. 常見不一致 + 修法：

# 情況 A：腳本已搬但 JSON 狀態沒更新
#   → 手動轉狀態
python scripts/ops/video-ops.py transition VID-NNN 已上線

# 情況 B：JSON 已更新但腳本沒搬
#   → 手動搬腳本（或讓 Claude 搬）
mv 03-production-line/02-ready-to-shoot/FILE.md 03-production-line/03-done/

# 情況 C：VID 建立了但腳本還沒存
#   → 正常，請 Claude 繼續存檔流程即可

# 3. 再次驗證
python scripts/ops/video-ops.py validate-all
```

**關鍵原則**：`pipeline.json` 是唯一真相源，資料夾位置只是整理。優先確保 JSON 正確。

---

## 場景 3：Google Sheets 同步失敗

**症狀**：`sync-to-sheets.py` 報錯（API error / 401 / 403 / timeout）

**恢復步驟**：

```bash
# 1. 確認是哪種錯誤
python scripts/utils/sync-to-sheets.py all 2>&1 | head -20

# 2. 常見錯誤 + 修法：

# 401 Unauthorized / 403 Forbidden
#   → credentials 過期，重新授權：
#   → 檢查 credentials 檔案是否存在
ls -la credentials/
#   → 重新執行 OAuth 流程（依照 Google API 設定）

# 404 Spreadsheet not found
#   → 確認 Spreadsheet ID 正確
cat scripts/utils/sync-to-sheets.py | grep SPREADSHEET

# Timeout / Network error
#   → 等幾分鐘重試
python scripts/utils/sync-to-sheets.py all

# 3. 確認同步成功
python scripts/utils/sheets-direct.py tabs
```

**注意**：Sheets 只是公佈欄，同步失敗不影響本地資料。本地 JSON + md 永遠是真相源。

---

## 場景 4：performance-patterns.json 被污染（錯誤的高表現提取）

**症狀**：生成的腳本持續使用某個效果不好的開場/CTA 模式

**恢復步驟**：

```bash
# 1. 檢查目前的 patterns
python scripts/ops/video-ops.py performance-report

# 2. 找到可疑的 pattern，確認是哪支影片帶進來的
#    看 vid_evidence 欄位，追溯到源頭影片

# 3. 從 git 歷史找到污染前的版本
git log --oneline data/kai/performance-patterns.json
git diff <before-commit> <after-commit> -- data/kai/performance-patterns.json

# 4. 選擇修復方式：

# 方式 A：還原到污染前版本
git checkout <clean-commit> -- data/kai/performance-patterns.json

# 方式 B：只移除特定 pattern（讓 Claude 幫忙編輯）
#   → 告訴 Claude：「移除 performance-patterns.json 中 VID-NNN 的所有提取」

# 5. 同時修正源頭影片的表現分類
#   → 告訴 Claude：「VID-NNN 的表現分類有誤，重新分類為普通/低表現」

# 6. 驗證
python scripts/ops/video-ops.py validate-all
```

**預防**：回填數據時仔細核對截圖數字，Claude 提取後先確認再存。

---

## 場景 5：整個 repo 需要從零恢復

**症狀**：本機資料全毀、需要在新機器上重建

**恢復步驟**：

```bash
# 1. 從 GitHub clone
git clone <repo-url> KaiOS-ContentSystem
cd KaiOS-ContentSystem

# 2. 安裝 Python 依賴（如有 requirements.txt）
pip install -r requirements.txt 2>/dev/null || true

# 3. 確認 credentials（Google Sheets 用）
# → 需要重新設定 OAuth credentials
# → 放入 credentials/ 資料夾

# 4. 驗證系統完整性
python scripts/ops/video-ops.py validate-all
python -m pytest tests/ -q
```

**預防**：確保每次重要操作後都有 commit + push 到 GitHub。

---

## 快速參考：常用還原指令

| 情境 | 指令 |
|------|------|
| 還原單檔到上一版 | `git checkout HEAD -- <path>` |
| 還原單檔到特定版本 | `git checkout <commit> -- <path>` |
| 看檔案修改歷史 | `git log --oneline <path>` |
| 比較兩版差異 | `git diff <old>..<new> -- <path>` |
| 看某版本的檔案內容 | `git show <commit>:<path>` |
| 全系統驗證 | `python scripts/ops/video-ops.py validate-all` |
| 跑測試 | `python -m pytest tests/ -q` |

---

## 重要原則

1. **不要慌，先跑 `validate-all`** — 讓系統告訴你哪裡不一致
2. **JSON 是真相源** — 資料夾位置、Sheets 都是次要的
3. **git 是你的後盾** — 任何檔案都能從 git 歷史還原
4. **Sheets 壞了不影響生產** — 本地資料完整就能繼續工作
5. **有疑問就問 Claude** — 描述症狀，Claude 會幫你診斷
