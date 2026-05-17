# 客戶 repo 引擎同步 SOP

> version: 1.1 | last_updated: 2026-04-23
> 給 Kai 看的操作手冊。每次升引擎後、客戶 repo 要同步時、照這份做。

---

## 背景：為什麼要這份 SOP

引擎 repo（`pei760730/KaiOS-ContentSystem`）**常駐 private**、客戶 repo（如 `KaiOS-Client-LongBroOS`）無法用 `git fetch` 直接抓。

**做法**：升完引擎後、主 repo **暫時 public 幾分鐘**、讓客戶 repo 跑 `/sync-engine` 抓最新、完成後立刻關回 private。

**為什麼不用 public mirror repo**：評估過、mirror 永久 public 的「被 fork 風險」你不接受。手動 public 雖然麻煩、但曝光 15 分鐘內爬蟲不一定完整爬到、可控。

---

## SOP 完整流程

### Phase 1：主 repo 開 public（Kai、~1 分鐘）

1. 確認你**剛 merge 完引擎升版 PR**（例如 v4.37 → v4.38）
2. 到 https://github.com/pei760730/KaiOS-ContentSystem/settings
3. 拉到底 **Danger Zone** → **Change repository visibility** → **Change to public**
4. 跳出警告、輸入 repo 名確認
5. 按 **I understand, change repository visibility**

⚠️ **這一刻起**：`01-data-brain/brand.md` / `cases.md` / `transcripts/` 等全部公開可見。目標是盡快關回、**縮短曝光時間**。

### Phase 2：告訴客戶 repo 的 Claude 執行同步（3-5 分鐘）

把下面這段貼給客戶 repo 那邊的 Claude：

```
KaiOS 主 repo 現在暫時 public。請立即執行：

1. git fetch engine main

2. 從 engine/main 取新引擎版本：
   git show engine/main:engine-manifest.json | jq -r '._meta.engine_version'

3. 跑 /sync-engine
   按 .claude/commands/sync-engine.md 流程、step 0 sanity check 會先驗證
   本 repo operator 是否已註冊在 data/.operators.json
   - 若無 → 先跑 bootstrap-client.sh --operator <代號> --brand <品牌> --confirm
   - 若有 → 直接進入 step 1 比對版本

4. 展示同步計畫（diff 檔案清單 + CHANGELOG 🔧 摘要 + blacklist 規則）

5. 我回「同步」後你執行、逐檔覆寫非 blacklist 檔

6. 完成後跑驗證：
   python scripts/lint/rules-lint.py
   python scripts/engine/engine_version_check.py
   python scripts/ops/video-ops.py --operator <你的 operator> validate-all

7. 若全綠：
   git add -A
   git commit -m "chore: sync engine vX.X → vY.Y"
   git push

全部過程盡快做完、完成後立刻回報我「✅ 完成」或「❌ 卡在 X」。
主 repo 正在暫時 public、每多一分鐘多一分曝光。
```

### Phase 3：關回 private（Kai、~30 秒）

客戶 Claude 回報「✅ 完成」**或**「❌ 卡在 X」**任一情況**、立刻：

1. 回 https://github.com/pei760730/KaiOS-ContentSystem/settings
2. Danger Zone → **Change visibility** → **Change to private**
3. 確認

⚠️ **即使失敗、也要先關再處理問題**。失敗可以下次重開重來、曝光時間不拖延。

---

## 曝光時間評估

| 情況 | 曝光時間 | 評估 |
|------|---------|------|
| 順利走完 | 5-10 分鐘 | 可接受、GitHub search index 可能來不及爬完 |
| 中間卡 | 15-30 分鐘 | 中等、可能被 cache、但關鍵敏感檔大概不會立刻被爬光 |
| 整晚沒關 | 12+ 小時 | 高風險、archive.org 和各種 mirror 可能完整抓到 |

**紀律**：客戶 Claude 回報（成功 OR 失敗）**立刻關回 private**、不糾結於完成度。

---

## 特殊情況處理

### 情況 A：新客戶第一次同步（operator 從未註冊）

客戶 repo 是剛建好、`data/.operators.json` 不存在時、`/sync-engine` step 0 會擋住：

```
❌ sync-engine step 0 sanity check 失敗：
   本 repo 當前 operator = <預設值或空> 未註冊於 data/.operators.json
   請先跑：bash scripts/bootstrap/bootstrap-client.sh \
     --operator <代號> --brand <品牌名> --confirm
   完成後再跑 /sync-engine
```

流程：
1. 客戶 Claude 跑 bootstrap（寫 `.operators.json` + 建空架構）
2. 再跑 `/sync-engine`（這次 step 0 過）

### 情況 B：客戶 repo 落後多版（跨越架構變更）

v4.37 → v4.38 涉及 `config.py` 架構改動（OPERATORS 從硬寫移到 `.operators.json`）。落後多個版本的客戶 repo 同步後：

1. **`.operators.json` 不存在** → config.py 會 fallback 到 DEFAULT_OPERATORS（只有 kai）
2. 客戶的 operator（非 kai）找不到 → video-ops.py 報錯
3. **解法**：跑 bootstrap-client.sh 註冊客戶自己的 operator

**順序重要**：必須**先 `/sync-engine` 拿到 v4.38 config.py**、**再 bootstrap**。反過來在 v4.9 config 上加 operator、同步後會被覆蓋。

### 情況 C：lessons.json migration（v4.35 之前客戶、v4.70+ 自動處理）

v4.36 合併三個 skill-memory JSON 為 lessons.json。**v4.70 起不需要手動 migration**：
- `scripts/ops/lib/lessons.py::load_lessons()` 有 **lazy auto-migration**、遇舊 stage / 舊欄位直接映射成 v2.0 schema
- 原 one-shot migration script `migrate_lessons.py` + `migrate_lessons_to_v2.py` + `migrate_lessons_v1_1.py` 於 v4.63 / v4.70 逐步退役

客戶 repo 從舊版（< v4.35）同步 v4.70+ 後、第一次 `load_lessons()` 即自動處理、無需額外動作。原 `data/skill-memory/*.legacy.json` 若存在、可手動刪除（Main repo v4.76 已清）。

---

## 版本升級後你的動作清單（Kai）

引擎新版本 merge 進 main 後：

- [ ] 記下新 engine_version（v4.XX）
- [ ] 確認要同步給哪些客戶 repo（目前：LongBroOS、未來：CITTA-VideoOS 等）
- [ ] 對每個客戶、依 Phase 1-3 SOP 走一遍
- [ ] 每個客戶 SOP 完成後立刻關回 private、再處理下一個
- [ ] 全部同步完、記入 CHANGELOG 或跟客戶 repo 的 `_meta.client.initialized_from_engine_version` 對齊

**批次 tip**：如果多個客戶要同時同步、**可以一次 public、讓所有客戶 Claude 各自並行跑 `/sync-engine`、全部完成再關 private**。但要協調（例如群組訊息同步通知）。

---

## 「不要用 `git pull engine main`」

**絕對不能用原生 `git pull`**。原因：

- `git pull` 會**整個 merge**、blacklist 保護失效
- 客戶的 `brand.md` / `cases.md` / `data/{operator}/` 會被引擎 repo 的 kai 版本覆蓋
- 這是災難、等於把客戶資料洗掉

**必須**用 `/sync-engine` slash command、它會：
- 逐檔讀 blacklist 規則
- blacklist 檔跳過、其他才覆寫
- 跑 `pytest` + `rules-lint` + `engine-version-check` 驗證
- 通過才 commit、不通過回報不 push

---

## 見證

這份 SOP 基於 2026-04-21 v4.38 合併時的現況寫成。未來如果：
- 變成 public mirror 模式（B 方案）→ 本 SOP 廢止
- Claude Code 放行 GitHub outbound → 直接 fetch 不需要 public、本 SOP 廢止
- 自動化機制成熟（如 GitHub App + deploy key）→ 本 SOP 改版

目前路徑走「手動 public」、本 SOP 為主要操作手冊。
