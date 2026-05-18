# /check — 大腦健康度

執行：

```bash
python scripts/ops/video-ops.py health
```

切 operator 加 `--operator <code>`：

```bash
python scripts/ops/video-ops.py --operator alex health
```

## 輸出 dimensions

每項顯示原始數字、**不算 overall score**（不同行業對「夠不夠齊」標準不同、避免單一閾值誤導）：

- **brand.md**：MVP 5 sections 填寫進度 + 全 14 sections 完成 % + 缺哪幾項
- **cases.md**：案例填寫筆數
- **personas/**：primary / partner 是否存在（檔名由 operator config 解析）
- **operators**：enabled 數量 + key 清單
- **pipeline**：items 總數 + 各 status 計數
- **lessons**：soft / hardened / archived 各態筆數
- **todos**：open / pending / in_progress / closed 計數
- **patterns**：proven_openings / ctas / formulas / risks 各筆數
- **transcripts/**：md 檔數

## Claude 讀完輸出後的判斷

讀完報告後依以下訊號決定要不要主動提醒 Kai（**不阻塞、不 gate**、只是訊號）：

| 訊號 | 行動 |
|------|------|
| 缺任一 MVP brand section | 提醒：建議先補完 MVP 才開拍（[0][1][2.5][3][5] 任一未填、不該跑 generation skill）|
| brand 50%+ 填 + pipeline 0 items | 可建議跑 `/init` 結尾或開第一支選題 |
| 已上線 ≥ 3 + lessons 0 | 提醒：可開始沉澱第一批 lessons |
| todos open ≥ 5 | 提醒：先處理待辦再開新工作 |
| personas/ 全缺 + brand 已填 50%+ | 提醒：建議建 primary persona 補人格層 |
| 模板 placeholder（`\{\{BRAND_NAME\}\}`）仍在 | 提醒：客戶 onboarding 未完成、跑 `/init` |

不算 overall score、Claude 自己看數字推理、保留行業差異彈性。

## 為什麼這條 command 存在

對應前次架構分析「狀態不可觀察」盲點。沒有可視化 → 客戶 + Claude 都靠感覺判斷「準備好了沒」。本 command 把可算的指標 surface 出來、推理工作回歸 Claude。
