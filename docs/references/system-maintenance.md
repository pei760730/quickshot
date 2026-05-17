# 系統維護參考

> 按需載入：「記錯」「lessons list」「升版 Skill」「選題去重」時讀取。

---

## 錯誤記憶管理（v2.0 lessons）

錯誤記錄存在 `data/[operator]/lessons.json`（`origin=mistake`），詳見 `docs/contracts/lessons-schema.md` v2.3+。v4.36 前的 `data/skill-memory/claude-mistakes.json` 三檔已合併、v4.78 API 層清除。

### 記錯流程

`記錯：XXX` →
1. Claude 在對話中：分類（幻覺/格式/流程）+ 寫 counter_pattern（correct_behavior）+ source_note（context）
2. 呼叫 `video-ops.py 記錯` （內部走 `record_mistake()` → `add_lesson(origin="mistake", stage="soft")`）
3. 若 Claude 判斷已達硬化強度 → 對話中提議 `/harden L-XXXX 為 <path>`、Kai 同意 → 當場落 test / lint / CLAUDE.md 禁令 / workflow.md / brand.md
4. Kai 不硬化 → lesson 保留 `stage=soft`、下次生成時由 generation skill 主動載入避開

### 查詢 / 歸檔

- `video-ops.py lessons list --origin mistake` — 列所有錯誤類 lessons
- `video-ops.py lessons list --origin mistake --stage soft` — 只列 active
- `video-ops.py lessons stats` — 看 stage 分佈（soft / hardened / archived）
- `video-ops.py lessons archive L-XXXX --reason "..."` — 歸檔單條

### 畢業 → 硬化

「畢業（graduated）」概念於 v4.63 降維時被 **`stage` 升級** 取代：
- 原 `graduated=true` → 現 `stage=hardened`（由 `/harden` 寫入對應 test / lint / 禁令 / brand.md 後升）
- 原 `graduated=false` 的 active → 現 `stage=soft`
- 原 `mistakes-archive` CLI（搬 graduated 到 jsonl）→ 現 `lessons archive` + 或讓 `/harden` 成功後自動升 hardened

## 偏差記錄定位

偏差記錄存在 `data/[operator]/lessons.json`（`origin=deviation`）：`diff-script` 命令比對腳本 vs 字幕、差異寫入 lessons。v4.36 前的 `data/skill-memory/script-deviations.json` 已合併進 lessons.json。

主要洞察來源是每次回填後即時沉澱（對話態）、lessons.json 負責長期累積與追溯、不作為唯一決策來源。

---

## 版本連動同步（必遵守）

任何檔案版本更新時，Claude 必須自動同步所有關聯副本。不需 Kai 提醒。

### 觸發 → 連動清單

| 觸發事件 | 必須同步的檔案 |
|---------|--------------|
| **Skill 升版** | ① SKILL.md frontmatter `version:` + heading `# v` ② `.claude/skills/[skill].md` stub description 版本號 ③ `02-skill-factory/README.md` 版本欄 ④ SKILL.md 版本紀錄表 ⑤ `07-changelog/CHANGELOG.md`（視規模） |
| **新 Skill 建立** | 上述全部 + ⑥ `.claude/skills/[skill].md` 新建 stub ⑦ `shared-references/data-brain-manifest.md` 依賴矩陣（若綁數據大腦） |
| **shared-references 更新** | ① 該檔 `> version:` 標頭 ② `quality-gates.md` 若引用數字有變 |
| **數據大腦內容更新** | ① `brand.md` / `cases.md` 對應模組的 `<!-- last_updated -->` ② `01-data-brain/index.md` 進化紀錄 |
| **系統規則更新** | ① 該檔 `> version:` 標頭 ② `07-changelog/CHANGELOG.md` |
| **契約更新** | ① 該契約 `> version:` 標頭 ② `07-changelog/CHANGELOG.md` ③ 通知對方代理 |

### 原則

- **一次改完**：不分批、不「下次再補」，同一個 commit 內完成所有連動
- **heading 為版本 SSoT**：SKILL.md 的 `# skill-name vX.XX` 是權威版本，frontmatter 和 stub 跟隨
- **CHANGELOG 門檻**：功能性變更必記、純格式修正可省略

---

## 選題去重 + 飽和偵測

生成標題/選題前，先執行 `video-ops.py list-topics` 取得已佔用主題。
完全相同或語意高度重疊 → 禁止推薦。cooldown 靈感 → 標註供 Kai 判斷。

**飽和偵測**：讀 pipeline.json 最近 5 支已上線影片的主題，按類型分群（成本/心態/日常/案例/知識）。若同類 ≥ 3 支 → 提醒「最近偏重 [類型]，建議換類型」。不阻塞，Kai 可覆蓋。
