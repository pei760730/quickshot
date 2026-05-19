# /init — 新客戶 day-1 一站式 bootstrap

> Claude-driven 對話、5 步把 template 帶到「最小可生產」狀態。
> 完成後跑 `/check` 看健康度、再走 `確認要拍：第一支主題`。

## 觸發

| Kai 說 | 動作 |
|--------|------|
| `/init` | 啟動本流程 |
| `新客戶開始` / `onboarding` / `從頭開始設定` | 同上 |

## Step 0：偵測現況、避免重複 onboard

跑 `python scripts/ops/video-ops.py health` 讀目前狀態：

- **若 brand.md MVP ≥ 3 填 + operators ≥ 1 非 default + 模板 placeholder 已替換** → 報「✓ 此 repo 看起來已 onboarded、用 `/check` 看狀態、不重跑 /init」、退出
- **否則繼續 Step 1**

## Step 1：品牌名（寫 CLAUDE.local.md）

問 Kai：「**品牌名是什麼？**（會寫進 CLAUDE.local.md、所有對話會看到這個名字）」

收到答覆後：
1. Read `CLAUDE.local.md`、`01-data-brain/brand.md`、`01-data-brain/cases.md`（三檔都帶 placeholder）
2. 把 `{{BRAND_NAME}}` 全部替換成 Kai 給的品牌名（3 個檔都動）
3. 把 `{{INIT_DATE}}` 替換成今日（YYYY-MM-DD）（3 個檔都動）
4. 展示 diff、Kai 說「OK」才 Write

## Step 2：operator 註冊（寫 data/.operators.json）

問 Kai 兩個問題：

1. **operator key**（英文小寫、用做檔案路徑、例：`alex` / `mary` / `team-a`）
2. **display name**（中文 / 對話顯示用、例：「Alex」「Mary」「A 隊」）

收到答覆後：
1. Read `data/.operators.json`
2. 在 `operators.{key}` 加新項目：
   ```json
   {
     "display_name": "<display>",
     "brand": "<step 1 品牌名>",
     "data_dir_rel": "data/{key}",
     "production_dir_rel": "03-production-line",
     "enabled": true,
     "created_at": "<today YYYY-MM-DD>"
   }
   ```
3. 展示 diff、Kai 確認、Write
4. 複製 `data/template/` → `data/{key}/`（用 `cp -r` 或 Python shutil）
5. 同步替換 `CLAUDE.local.md` 內的 `{{OPERATOR_KEY}}` → `<key>`、`{{OPERATOR_LABEL}}` → `<display>`（Step 1 已把 `{{BRAND_NAME}}` / `{{INIT_DATE}}` 替換、Step 2 補完 operator 兩個 placeholder）

## Step 3：主創作者 persona

問 Kai：「**主要創作者叫什麼？**（會建 `01-data-brain/personas/{name}.md`、是腳本對齊的人格參考）」

收到答覆後：
1. 把名字轉成檔名格式（lowercase、空格換 `-`、例：「Alex Wang」→ alex-wang.md）
2. 複製 `01-data-brain/template/personas/PRIMARY.md` → `01-data-brain/personas/{filename}`
3. 把 `{{PERSONA_NAME}}` 替換成 Kai 給的名字
4. Edit `data/.operators.json` 該 operator 加 `"primary_persona_file": "{filename}"`
5. 展示新建檔案路徑、提示「persona 內容（說話風格 / 觀點 / 禁區 / 野心）等 Kai 拍幾支後再回頭填、不阻塞」

## Step 4：brand.md MVP 5 sections

問 Kai：「**接下來填 brand.md MVP 5 sections、每個問你 2-3 個問題。準備好了嗎？**（任意一題說 `跳過` 就跳）」

照順序問：

### [0] 基本資料
1. 業務性質一句話？（例：手搖飲料連鎖、B2B SaaS、補習班）
2. 主要市場 / 規模？（例：台灣 50 店、全球線上）
3. 年度目標一句話？

### [1] 核心專長
1. 創辦人最能打的能力是什麼？（≤ 10 字）
2. 一個能拿出來秀的具體數字？（例：管 100 店 / 服務 5000 客戶）
3. 跟同業最大差異？

### [2.5] 高流量素材庫
1. 個人故事：你最常被觀眾說「這段超讚」的故事是哪一段？
2. 行業誤會：外人最容易誤會你們行業的什麼？
3. 圈內事：圈內人才知道、外人不知道的一個冷知識？

### [3] 內容調性
1. 你想被觀眾覺得是什麼樣的人？（3 個形容詞）
2. 你不會講的話 / 不會用的詞？（例：不講「賦能」這種商務詞）
3. 講話節奏：偏長段論述 / 短句快節奏 / 對話互動？

### [5] 禁忌（短期客戶踩一次完蛋、必填）
1. 不能點名的競品？
2. 不能講的數字 / 機密？
3. 不能碰的話題（政治 / 宗教 / 家人 / 其他）？

每個 section 收完答覆後：
1. 草擬 brand.md 對應 section 的內容（用 Kai 答覆 + 用戶風格、不亂加事實）
2. 展示草稿給 Kai 看、Kai 說「OK」才寫
3. 寫入後同步把該 section 的 `<!-- last_updated: -->` 改成 `<!-- last_updated: YYYY-MM-DD -->`

## Step 5：歷史素材（cold-start 觸發）

問 Kai：「**有過往訪談 / podcast / 文章 / 語音嗎？3-10 篇就夠**（有就丟給我、自動跑冷啟動萃取流程；沒有就 skip）」

- **有** → 走 `.claude/rules/workflow.md` §冷啟動萃取流程（音檔轉譯 / 跨篇盤點 / 候選清單三色標記）
- **沒有** → skip、提示「之後有素材隨時 `冷啟動：[檔案]` 觸發」

## Step 6：完成、跑 /check 顯示成果

最後一步：
1. 跑 `python scripts/ops/video-ops.py --operator {key} health` 顯示完整 dimension snapshot
2. 報告：「✓ onboarding 完成、現在可以說『確認要拍：[第一支主題]』開拍」
3. 如果 brand.md MVP 仍有缺、明確列出建議補完項目

## 設計原則

- **每步寫前確認**：禁令 #2「禁止未經使用者確認就存檔」
- **跳過彈性**：任何 step 可 `跳過`、不強迫
- **idempotent**：Step 0 偵測已 onboard 直接退出、避免覆蓋
- **問題清單從 brand.md schema 動態 derived**：未來 brand.md schema 改變、init 問題自動跟著改、不寫死

## 為什麼這條 command 存在

對應前次架構分析「新功能 #1」/「客戶 day 1 不知道從哪開始」結構性盲點。
把散在 README + CLAUDE.local.md template + workflow.md §冷啟動萃取 + 14 sections brand.md 的 onboarding 動作、整合成單一 Claude-driven 對話。

template 從「museum」變回「短期客戶開拍即用的工具」。
