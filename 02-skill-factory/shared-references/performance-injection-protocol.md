# 表現模式注入協議（所有生成型 Skills 統一）

> version: 4.0 | last_updated: 2026-06-14
> 自動執行，不需 Kai 觸發。數據不足 → 跳過，不阻塞。
>
> **v4.0（短期客戶 template 誠實化）**：移除 v3.0「前景軌（case-based 自動注入）」。
> 實況核對：前景軌的注入函式 `scripts/utils/lib/performance_injection.py:build_injection_payload()`
> **從未被任何生成 skill 接入**（零 importer、屬「設計了但沒接線」的 consumption theater）、已刪。
> 保留**唯一真實在運作**的機制：背景軌 aggregate 注入 —— `brain_loader` 每次生成自動把
> `performance-patterns.json` 載進 skill context。短期客戶要的是「用前面幾支真實有效的 pattern
> 讓後面更好」、這條背景軌已滿足；case-based RAG 是長期經營型的 over-engineering、不保留。

---

## 唯一機制：背景 aggregate 注入（brain_loader 自動）

| 來源 | 內容 | 接入點 |
|------|------|--------|
| `data/[operator]/performance-patterns.json` | 全局勝率統計（proven_openings / proven_ctas / proven_formulas / risk_patterns）| `scripts/libs/brain_loader.py` 每次生成載入 `BrainContext.performance_patterns`、傳進 skill |

**為什麼夠用**：4.7 推理力下、把「已驗證高勝率的開場 / CTA / 公式 + 已知風險模式」整批餵進生成 context，
LLM 自會挑相關的用。短期客戶 30 天樣本量本就不大、aggregate 已涵蓋「用什麼有效」這個需求。

## 注入欄位

| 欄位 | 內容 | 注入門檻 |
|------|------|---------|
| proven_openings | 已驗證高表現的開場類型 | ≥ 2 支影片驗證 |
| proven_ctas | 已驗證高表現的 CTA 類型 | ≥ 2 支影片驗證 |
| proven_formulas | 已驗證的腳本公式結構 | ≥ 2 支影片驗證 |
| risk_patterns | 已知失敗模式 | 有記錄即迴避 |

## 計算指標（每次回填後由 `backfill` → `patterns` 自動更新進 performance-patterns.json）

每個 proven pattern 自動攜帶以下指標：

| 欄位 | 計算方式 | 用途 |
|------|---------|------|
| `sample_size` | len(vid_evidence) | 高表現證據數 |
| `total_uses` | 所有已回填影片中使用此 pattern 的數量 | 分母（含高/普/低） |
| `win_rate` | sample_size / total_uses | 勝率 |
| `confidence` | low（<3 次使用）/ medium（3-7）/ high（≥8） | 信心等級 |
| `last_evidence_date` | 最近一次加入證據的日期 | 時效性判斷 |

## 信心等級與注入力度

| 信心等級 | 條件 | 注入方式 |
|----------|------|---------|
| **high** | total_uses ≥ 8 | **強烈推薦**：「📊 此類型勝率 N%（8+ 次驗證）」，優先選用 |
| **medium** | 3 ≤ total_uses < 8 | **建議參考**：「📊 此類型 N 次高表現（勝率 N%）」 |
| **low** | total_uses < 3 | **僅供參考**：照舊邏輯，不額外強調 |
| **degraded** | 有 degraded 旗標 | **降級警告**：「⚠️ 此模式近期表現下滑」 |

## 核心規則

1. 成功模式（proven_*）→ 作為**額外範例**，注入力度隨 confidence 調整
2. 失敗模式（risk_patterns）→ 生成時**主動迴避**
3. 資料為空或欄位不足門檻 → **跳過**，不影響流程
4. win_rate < 30% 的 proven pattern → 降為「僅供參考」，不主動推薦

## 多維度交叉分析（手動、回填 ≥ 10 筆後 Claude 可在對話中跑）

`backfill.py:cross_dimensional_stats()` 可取得 by_hook_type / by_version / by_topic_type / by_skill /
combinations（hook × version 勝率排行）。**這是 Claude 分析回填時的手動工具、不是自動注入鏈的一環。**
生成時依 topic_type + version 篩選最相關的 pattern 推薦，而非給全部列表。

## 相似 VID 查詢（手動 CLI、非自動注入）

`video-ops.py retrieval`（底層 `scripts/utils/lessons_retrieval.py`）可手動查同類 VID
（topic_tags overlap 50% + performance tier 30% + time decay 20%）。
**v4.0 起明確定位為「Claude / Kai 對話中手動參考」工具、不再宣稱自動注入進生成 prompt。**
（原 v3.0 宣稱的 case-based 自動前景注入從未接線、已隨 `performance_injection.py` 一併移除。）

## 各 mode 注入重點（generation skill 5 modes、皆走背景 aggregate）

| mode | 背景注入（aggregate）|
|------|---------|
| dual-track | proven_openings + proven_formulas + risk_patterns |
| variant | proven_openings → 各變體開場、proven_ctas → 收尾 |
| series | proven_openings → 第 1 集 + 高潮集 |
| interview | proven_openings → 第一個 Q 字卡、proven_ctas → 結尾 A 爆點 |
| viral | 不綁背景（per brain-loading.md：viral 不綁大腦）|

## 失敗 fallback

- `performance-patterns.json` 不存在 / 欄位空 → aggregate 空、純 LLM 從 brand.md 推理、不阻塞
