# 生產線完整步驟

> 按需載入：「確認要拍」「存檔」「回填」「語音筆記」「複製贏家」時讀取。
> CLI 完整參數見 `docs/contracts/video-ops-cli.md`。

---

## 確認要拍（完整 10 步）

`確認要拍：XXXX` →
1. `video-ops.py confirm IDEA-NNN --title "標題"` 分配 VID
2. 載入數據大腦（讀 `01-data-brain/index.md` 依指引載入）
3. （選擇性）外部主題研究 — 靈感為 timely/trending 或涉及時事時主動建議，Kai 說「先研究一下」可手動啟用，不阻塞可跳過（Wave C 後 `scripts/tools/research.py` 提供）
4. 套用 `shared-references/title-rules.md` → 10 組標題（5 類 × 2），推薦最有衝突感的
5. 🔒 Kai 選標題 + 選 mode（預設 generation mode=dual-track）
6. 執行 generation skill 生成腳本
7. quality skill phase=fix 掃描去 AI 味（24 patterns、見 `shared-references/ai-pattern-detection.md`）+ 套用 `shared-references/templates/hook-templates.md` 三秒金句（自動）
8. 🔒 Kai 看腳本 →（選擇性）`語音筆記` 修正產業細節
9. 🔒 Kai 說「存檔」才寫入
10. quality skill phase=check 5 項品質檢查（存檔前自動）→ 🟢通過存檔 / 🟡提醒 / 🔴建議修改

---

## 存檔

1. 寫入 `03-production-line/02-ready-to-shoot/YYYY-MM-DD_主題_腳本_V1.md`
2. `video-ops.py save VID-NNN --script-path "路徑" --title-type T? --hook-type B?/D? --version B2 --verifier-prediction high/normal/low [--skill generation --mode dual-track]`（前 5 項必填）
   > 合法 enum 值以 `pipeline.json _meta.valid_*` 為 SSoT（見 `docs/contracts/pipeline-schema.md`）。
3. 品質細項存檔：`video-ops.py record-verifier-scores VID-NNN --conflict-score N --retention-prediction LEVEL --ai-residue-count N --data-consistency true|false --format-complete true|false --pass-count "N/5"`（存檔時自動執行）
4. **生成規則自動沉澱**：`record-verifier-scores` 累積後，`propose_rules_from_verifier()` 自動偵測重複品質問題（AI 殘留 ≥3 次 / 衝突感 ≤4 分 ≥3 次 / 數據不一致 ≥3 次）→ 提議寫入 `data/[operator]/lessons.json`（`origin=verifier`、Kai 確認才寫入；v4.36 前舊路徑為 `generation-rules.json`）

---

## 回填

Kai 提供 IG 截圖 → 讀數字 → **列出所有讀到的數字讓 Kai 確認**（防止 OCR 誤讀污染數據）→ 確認後 `video-ops.py backfill` → 高/低表現自動提取學習到 performance-patterns.json → 回填後自動執行：

- 若該影片有 `verifier_prediction`：自動比對預測 vs 實際表現，寫入 `verifier_accuracy`（由 backfill 命令自動執行）
- **拍攝偏差自動比對**：問 Kai「字幕文字方便貼一下嗎？」→ `video-ops.py diff-script VID-NNN --subtitle '字幕全文'`（Kai 不想貼就跳過）
- **單支快速診斷**（每次回填後自動）：判定表現等級 → 交叉比對同類 → 一句話歸因 → `📊 快速診斷：[一句話]`（同類不足 3 支標註「樣本不足」）
- **回填即洞察**：勝敗模式比對 + 趨勢一句話（對話中 Claude 主動判斷、非自動 cron）

---

## 語音筆記

Kai 用手機錄音口述修正，丟音檔進 Claude Code 自動處理。不限於修正腳本 — 錄音中提到的新靈感、產業知識也會自動分流。

### 指令

`語音筆記` — 附音檔（.m4a/.mp3/.wav/.ogg/.flac/.aac）或直接貼逐字稿文字 + 可選腳本截圖

### 流程

1. Kai 丟音檔（+ 可選截圖）或直接貼逐字稿文字
2. 音檔：`python scripts/utils/transcribe.py [音檔路徑]` 轉文字；文字：直接進下一步
3. 列出轉譯結果讓 Kai 確認 — **粗體標出數字、金額、品牌名**（ASR 高風險區）
4. 自我修正偵測：同一主題多次講不同版本 → 取**最後一次**為準，明確標出
5. **原文完整保存**：存入 `01-data-brain/transcripts/YYYY-MM-DD_主題.md`
6. 語意拆解，每條獨立分類並處理：

| 類型 | 判斷依據 | 處理方式 |
|------|---------|---------|
| 腳本修正 | 提到特定段落/數字/觀念要改 | 配對 VID → 定位段落 → 展示修正差異 |
| 新靈感 | 提到未來可以拍的主題 | → `add-idea` 進靈感箱 |
| 產業知識 | 可重複使用的規則/結構/常識 | → 問「要更新到數據大腦嗎？」 |
| 想法/偏好 | 對腳本風格或內容方向的偏好 | → 記錄到 `data/[operator]/lessons.json`（v4.36 起、`skill-memory/` 已退役）|

7. 展示處理摘要，Kai 逐項確認才執行

### 腳本配對優先序

1. **明確 VID** — 語音中說「035 那支」→ 直接定位
2. **關鍵字語意** — 提到主題關鍵字 → 搜尋待拍/剪輯中腳本
3. **數字/金額匹配** — 搜尋腳本中包含該數字的段落
4. **截圖比對** — 讀截圖文字，比對 pipeline
5. **找不到** → 列出最近的待拍腳本讓 Kai 選

### 知識抽取過濾

只有**同時符合三個**才問 Kai：可重複使用 + 非單一案例修正 + 屬於規則/結構/常識。單純數字修正 → 只改腳本，不進大腦。

---

## 贏家複製

`複製贏家：VID-NNN` 或 `再來一支像 VID-NNN` →

1. 讀取該影片的 pipeline.json 資料（確認 performance = high）
2. 讀取其 learning 段 + script 原文
3. 提取勝出公式：hook_type + version + formula 結構
4. Kai 選新主題（或從靈感箱推薦同類型未拍主題）
5. 調用 generation skill mode=dual-track，將勝出公式作為硬約束注入
6. 後續流程與正常「確認要拍」相同

### 規則

- 僅限 performance = high 的影片
- 同公式連續最多 2 支 → 第 3 支時提醒「建議換公式」
- 新腳本的主題不可與原影片重複
- 複製的是**結構和節奏**，不是內容和故事
