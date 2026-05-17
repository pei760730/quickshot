# Skill × Data-Brain 依賴清冊（lint-driven、v3.1）

> version: 3.1 | last_updated: 2026-05-11 | v3.1: brand.md [1] 重命名「業務能力與優勢」、[3] 內容調性已遷至 personas/kai.md [1]（v4.97 personas/ 拆分）
> **定位**：本檔以前是手寫的 skill × brand.md section 對照表、Phase 5 退役 14 skill 名後過時。**v3.0 改為 lint-driven**：依賴關係由 `scripts/lint/brand_ref_lint.py` 從 SKILL.md 自動推導、本檔降為「設計說明 + 怎麼查當前 manifest」。
>
> **資料地圖 SSoT** = `01-data-brain/index.md`、不在本檔重複。

---

## 怎麼查當前 manifest（取代手寫矩陣）

```bash
python scripts/lint/brand_ref_lint.py --manifest

# 輸出範例：
# 02-skill-factory/discovery/SKILL.md: [3, 4, 5, 6, 10, 11, 12]
# 02-skill-factory/generation/SKILL.md: [5, 6]
# 02-skill-factory/quality/SKILL.md: [3]
# 02-skill-factory/shared-references/persona-deviation-scoring.md: [0, 2, 3, 5]
# ...

# JSON 格式（給其他工具用）：
python scripts/lint/brand_ref_lint.py --manifest --json
```

manifest 從以下兩個來源推導（lint 自動掃描）：
1. **frontmatter `brand-refs:`**（顯式宣告、SSoT）
2. **內文 `brand.md [N]` 引用**（lint 自動 grep）

不一致時 lint 警告：
- ❌ ERROR：引用 brand.md [N] 但 brand.md 沒這 section
- ⚠️ WARN：內文引用了但 frontmatter `brand-refs:` 沒列（under-declared）
- ⚠️ WARN：frontmatter 列了但內文找不到（over-declared）

---

## SKILL 端怎麼宣告

每個 SKILL.md frontmatter 加 `brand-refs:` 欄位、列出依賴的 brand.md section 數字：

```yaml
---
name: discovery
description: ...
version: 1.0
brand-refs: [3, 4, 5, 6, 10, 11, 12]
---
```

**規則**：
- 內文有 `brand.md [N]` 引用 → frontmatter 必列 N
- 不依賴任何 section → 寫 `brand-refs: []`（顯式聲明、避免 under-declared 警告）
- 數字 = brand.md section 編號（[0]-[12]、[8] 在 cases.md）

---

## 漂移偵測（v3.0 自動化）

### 觸發時機

- **CI**：`rules-lint.py --ci` 自動跑 brand_ref_lint、ERROR 阻塞、WARN 不阻塞
- **本地**：開發 SKILL.md / brand.md 時跑 `python scripts/lint/brand_ref_lint.py` 確認

### 設計目的

改 brand.md 某 section → 跑 lint 看哪些 SKILL.md 引用該 section → 知道哪些 skill 受影響、要不要重跑驗證。

### 為什麼從手寫改 lint

舊版（v2.3）手寫矩陣的問題：
1. 14 個舊 skill 名退役後即時過時、無人同步（直到 Phase 5b 才發現）
2. 新增 skill / 改 mode / 改 brand section 時、容易忘記更新
3. 矩陣本身就需要「漂移偵測的偵測」（meta-overhead）

v3.0 lint-driven：
- SKILL.md frontmatter 是 SSoT、矩陣是 derived
- skill 改了、frontmatter 跟著改、lint 自動同步
- 對應 `skill-design-principles.md` 準則 B（可變 lint 就 lint）+ 準則 C（規則化勝於文檔化）

---

## 模組簡介（人類可讀快速查表、不參與 lint）

> 這份表是 brand.md 各 section 的內容簡介、給 Claude / 員工看用、**不是** 依賴矩陣。實際依賴關係查 `brand_ref_lint --manifest`。

| 模組 | 內容 | 一般語境下哪些 skill 會用 |
|------|------|----------------------|
| [0] 基本資料 | 品牌名、店數、商業模式 | discovery / generation 全 modes |
| [1] 業務能力與優勢 | 供應鏈、爆品、SOP | discovery / generation mode=dual-track |
| [2] 目標受眾 | TA 畫像 | generation 各 modes（補充） |
| [3] *已搬遷* | → `personas/kai.md` [1] 說話風格 | quality phase=fix（核心）/ generation 全 modes |
| [4] 商業洞察 | 核心論點 | discovery（C 版切角推理用、generation 不直接引用、僅 dual-track 內生成參考）|
| [5] 禁忌與邊界 | 迴避話題、灰色地帶 | quality phase=check / generation 各 modes |
| [6] 競爭對手 | 敵人具象化素材 | discovery / generation mode=interview |
| [7] 平台策略 | CTA 風格、粉絲互動 | generation 各 modes |
| [8] 真實案例庫（cases.md）| 5 大案例 + 高表現記錄 | discovery / generation 全 modes |
| [9] 數據記錄 | 營業數字 | quality phase=check / generation D 版 |
| [10] 目標與規劃 | 2026 展店目標 | discovery |
| [11] 季節性 | 淡旺季 | discovery（節點選題） |
| [12] 其他補充 | 人生故事、價值觀 | discovery / generation mode=series + interview |

實際依賴以 lint manifest 為準、本表只是脈絡說明。

---

## 與其他文件的關係

| 文件 | 關係 |
|------|------|
| `scripts/lint/brand_ref_lint.py` | 真實 manifest 來源、本檔的 SSoT |
| `01-data-brain/index.md` | 資料地圖 SSoT、含進化紀錄 |
| `02-skill-factory/shared-references/skill-design-principles.md` v1.5 | 本檔對應準則 B / C / F |
| 各 `02-skill-factory/<name>/SKILL.md` frontmatter `brand-refs:` | 顯式宣告層 |

---

## 升版時機

- 改變 lint pointer / 命令 → 本檔同步
- skill / brand section 增刪 → **不需動本檔**（lint 自動同步）

不該頻繁修改。本檔是長期錨點。

---

## 版本歷史

- **v2.x**（2026-04 之前）：手寫 skill × brand section 矩陣、14 個舊 skill 名
- **v3.0**（2026-04-26）：Phase 5b 落地 — 改為 lint-driven、矩陣由 `brand_ref_lint.py --manifest` 自動推導、本檔降為設計說明 + 怎麼查 manifest。對應 T-0017、配對 PR #319（Codex `brand_ref_lint.py` 落地）+ 本 PR（5 核心 SKILL.md frontmatter 加 brand-refs）
