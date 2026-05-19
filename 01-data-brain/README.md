# 01 - Data Brain

> 客戶品牌知識庫（短期客戶 template、品牌名見 `CLAUDE.local.md`）

## 結構

```
01-data-brain/
├── index.md          # 載入索引 + 進化觸發（資料地圖 SSoT）
├── brand.md          # 品牌知識（[0]~[12] sections、lazy load）
├── cases.md          # 案例庫 + 高表現記錄
├── personas/         # operator 對應的人格檔（檔名由 data/.operators.json 解析、首次 onboarding 時建）
├── template/         # 新客戶 bootstrap 用的空白模板
└── transcripts/      # 語音筆記原文（批次沉澱用、首次 `語音筆記` 時自動建立、未追蹤前不存在）
```

## 使用原則

- 腳本生成前必讀 `index.md`，依指引載入
- 不在大腦中的資訊不能編造
- 標記「請補充」的區塊需 Kai 填入實際數據
