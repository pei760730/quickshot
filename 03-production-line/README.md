# 03 - Production Line（生產線）

> 端到端內容生產管線：靈感 → 腳本 → 拍攝 → 上線 → 數據追蹤

## 管線結構

```
03-production-line/
├── 01-inspiration-inbox/       # （已廢除，靈感由 pipeline sharded SSoT 管理）
├── 02-ready-to-shoot/          # QA 通過、等待拍攝的腳本
│   └── {operator}/             # 每 operator 一個子目錄
└── 03-done/                    # 已上線存檔
    └── {operator}/
```

**配套追蹤**：`data/{operator}/pipeline/`（sharded SSoT — `_meta.json` + `items/VID-NNN.json` / `IDEA-NNN.json`、見 `docs/contracts/pipeline-schema.md` v2.1+。legacy 單檔 `pipeline.json` 已退役、`.gitignore` 防誤建）

## 工作流程

```
0. 靈感捕捉  → pipeline [inbox]（隨時丟）
1. 靈感整理  → [inbox] → [selected]（整理靈感）/ [cooldown]（暫緩）
2. 確認要拍  → 說「確認要拍：XXXX」→ 生成 VID-NNN + 生成腳本
               → humanizer → hook-killer → script-verifier（存檔前）
               → 腳本存入 02-ready-to-shoot/{operator}/，影片追蹤 [待拍]
3. 剪輯階段  → 「剪輯中：VID-NNN」[剪輯中]
4. 上線      → 「上線：VID-NNN」→ 腳本移 03-done/{operator}/，影片追蹤 [已上線]
5. 數據回填  → 上線後 24-72 小時，提供截圖 → 回填 + 學習提取
```

**品管模式**：script-verifier（預設標準模式）。切換「嚴格模式」可讓紅燈阻塞存檔。

## 卡關時限

| 階段 | 正常時限 | 超時 → |
|------|---------|--------|
| 靈感 [inbox] | ≤ 7 天 | ⚠️ 卡關 |
| 靈感 [selected] | ≤ 14 天 | ⚠️ 卡關 |
| 待拍 | ≤ 7 天 | ⚠️ 卡關 |
| 剪輯中 | ≤ 7 天 | ⚠️ 卡關 |
| 數據回填待辦 | 上線後 3 天 | 🔴 逾期 |

---

## 孤兒檔案處理 SOP

> 「孤兒」= 磁碟上有 `.md` 腳本檔，但 pipeline 無 VID 指向（或反之）。
> 2026-04-17 首次全面清理（PR #124、#129），kai 區從 32+5 orphan 降為 0。

### 兩類孤兒

| 類型 | 症狀 | 風險 |
|------|------|------|
| **磁碟 orphan** | disk 有檔，pipeline 無 VID `script_path` 指向 | 污染生成背景讀取；未來稽核難 |
| **Pipeline orphan** | pipeline `script_path` 指向，disk 檔不存在 | script-verifier 讀取失敗；上線流程卡 |

### 檢查指令（以 CLI 為準）

```bash
python3 scripts/ops/video-ops.py list-orphans
```

CLI 已實作、取代過去的 one-liner 臨時檢查。**不要手改 pipeline 檔案**（`pipeline/items/*.json` shards）— 所有 orphan 處置用下方 CLI 子命令。

### 處置決策樹

```
disk orphan
├─ 檔名含 VID-XXX（已刪 VID 殘留）         → 刪檔（git 歷史保留）
├─ 主題對得上某 script_path=None 的 VID    → 用 `video-ops.py save VID-NNN --script-path "..."` 補
├─ 主題對得上已刪除的 inbox/archived 靈感  → 刪檔
└─ 主題無對應 VID 也非殘留                 → 留原位 + 在 todo 記錄「待 Kai 決策：建 VID 或刪」

pipeline orphan（script_path 指向不存在的檔）
├─ VID 是待拍狀態                           → 改 script_path=null（腳本還沒寫）
├─ VID 已上線但檔案被誤刪                   → git 歷史還原
└─ VID 是 quick-shot 補登（script_status=待補）→ notes 記錄 + script_path 保留追跡
```

### 歸檔策略（已上線 + 已回填 VID）

**預設**：腳本保留在 `03-done/{operator}/`，不再移動。
**例外**：
- 腳本檔超過 6 個月 + backfill 完成 + learning_extracted=true → 可考慮歸檔到 `03-done/archive/YYYY/`（目前未實作，需要時再建）
- VID 下架（如 VID-026 無尊&無飲）→ 檔案刪除（git 保留），todo 記錄理由

---

**版本**：v4.5
**最後更新**：2026-04-21（v4.38：Ruby operator 完全移除、3 支 orphan 腳本歸檔刪除）
