# Agent Collaboration Charter

> version: 1.10 | last_updated: 2026-04-26
> 雙方契約：Claude Code + Codex
> 觸發方式：Kai 說「掃描」「scan」「scan-top3」→ 各代理讀此檔並執行
> **v1.10 (2026-04-26)**：§Codex 任務 prompt 模板 §必須前綴 加 step 1.5 — 任務指令含模糊動作詞（「補一行」「修一下」「處理」「澄清」等）時 Codex 必停下、留 PR comment 回問 Kai 動作位置、不預設開新 PR。根因：L-0021 v1.9 把規則寫進「Codex 側紀律」段落、但 Codex 不讀 repo markdown、需直接寫進每次 task 都帶的 prompt 模板才生效。
> **v1.9 (2026-04-26)**：§Codex 任務 prompt 模板擴充 — Pre-flight territory check（path 對照 CODEX_OK 預檢、避免 task prompt 要 Codex 改 Claude 領土）+ Action location must be explicit（明寫 edit PR body / 修檔案 / 開新 PR、避免 Codex 預設選「開新 PR」）+ sandbox no-origin fallback。根因：L-0021、PR #327/#328 連續觸發兩種錯（territory 違規 + 動作位置誤判）。
> **v1.8 (2026-04-24)**：§9 追加 §9.11 Cross-territory engine bump 規則（解 #271/#272 rescue 問題）+ §9.12 Codex task base check 強制（解 #276 stale base 重做）。根因：兩個 pattern 各自導致一次 overlap / duplicate PR、值得進 SOP 正式化。
> **v1.7 (2026-04-24)**：§9.3 責任區從 soft rule 升級為 hardened（`.github/workflows/territory-lint.yml` CI gate + CLAUDE.md 禁令 #8）。根因：Wave 1/2 Claude 違反 §9.3 寫入 Codex 領土、造成 #260/#261 overlap。

---

## 0. 角色邊界（必須遵守）

- 只掃描與評估「你負責的區域」
- 不評估/改動對方責任區的內部實作
- 可指出跨區接口風險，但不可越界定義對方內部方案
- 若關鍵問題根源在上游/跨區 → 標記「跨區契約議題」

---

## 1. 責任區定義

### Claude 責任區（prompt / skill / content system）

- `.claude/**`
- `CLAUDE.md`
- `02-skill-factory/**`
- `01-data-brain/**`
- `00-control-center/**`（recovery-playbook / employee-reports / 拍攝清單等；`todo/` 目錄 v4.73 退役、待辦已遷 `data/<op>/todos.json`）
- `03-production-line/**`
- `07-changelog/**`

### Codex 責任區（backend / CI / tooling）

- `scripts/ops/**`
- `scripts/utils/**`
- `scripts/lint/**`
- `.github/workflows/**`
- `tests/**`
- `data/**/*.json`（僅限由 Python 腳本管理之 schema/資料）

### 共享契約（雙方接口）

- `docs/contracts/**`

---

## 2. 評估準則（4 個最高優先方向）

若與局部最佳化衝突，優先這 4 項：

| 方向 | 定義 |
|------|------|
| **更第一性原理** | 不預設現有架構合理，先重建問題本身。先定義本質目的、最小成立條件、必要控制點；若現有設計偏離本質，優先重建而非修補 |
| **更智能** | 用更少的控制點、更清楚的責任邊界、更穩定的資料流，解決更多關鍵問題。不顯著增加複雜度、維護成本與治理負擔 |
| **更可自我進化** | 不只解決眼前問題，還要能沉澱規則、降低未來重工與人工補洞成本，讓下一輪更容易做出更好決策 |
| **更能彼此配合** | 不能只讓自己變強，還要避免和其他模組、流程、資料結構打架，不能破壞整體一致性 |

---

## 3. 掃描任務（兩階段）

### 第一階段：責任區全局掃描

在你的責任區內判讀：
- 各資料夾角色
- 各模組的責任邊界
- 主要資料流與控制點
- 哪些地方耦合過深、責任錯位、重複控制、假智能化、假閉環、假治理
- 哪些地方表面正常、實際是未來容易失控的隱性瓶頸
- 哪些定義和 `docs/contracts/` 有不一致或冗餘

### 第二階段：前 3 名高槓桿深挖候選

只選你責任區內最值得深挖的前 3 名，不平均分配注意力。

「項目」可以是：資料夾 / 模組 / 流程 / 一組強耦合檔案 / 結構問題。

---

## 4. 篩選標準（排序依據）

優先選出那些：
1. 最偏離第一性原理的地方
2. 最影響整體智能化程度的地方
3. 最妨礙自我進化的地方
4. 最容易和其他模組互相打架的地方
5. 一旦規模放大最容易失控的地方
6. 局部看合理，但其實拖累整體一致性的地方
7. 單獨拉出來深挖後，最可能帶來整體槓桿提升的地方

---

## 5. 分析要求（每個候選都要做）

- 本質目標是什麼
- 目前最深層瓶頸是什麼
- 問題在本項目內，還是在更上游
- 若問題在對方側 → 標記「跨區契約議題」
- 若單獨拉出來優化，值不值得現在做
- 它和其他模組的接口、責任邊界、資料流是否清楚
- 它的局部優化是否可能破壞整體一致性
- 它是該深挖、延後、還是封版

---

## 6. 跨區協作要求

對每個前 3 項目，額外輸出：
- 涉及的跨區接口（若有）
- 對方代理需要配合的「最小契約」
- 若不對齊，最可能發生的失配風險
- 你這邊可先獨立推進的部分 vs 必須等待對齊的部分

---

## 7. 輸出格式

掃描報告需涵蓋 **判讀 → Top3 → 取捨 → 下一步 → 委託** 五個面向。Top3 和委託段是必產出（有下游動作），其餘可合併濃縮。

### 必產出 1：Top3（每項含欄位）

| 欄位 | 說明 |
|------|------|
| 項目名稱 + 類型 | 資料夾 / 模組 / 流程 / 結構問題 |
| 為什麼進前 3 | 最深層問題 + 不處理會怎麼爆 |
| 預期槓桿 | 連鎖改善範圍 |
| 跨區接口 | 無則寫「無」 |
| Owner | Claude / Codex / Shared |
| Blocking | Yes / No |

### 必產出 2：給對方代理的同步掃描委託（✂️ 可複製段）

```
### 📬 同步掃描請求（給 [Codex / Claude]）

**起因**：[本方] 於 YYYY-MM-DD 跑 /scan，發現以下跨區議題。

**跨區議題**（本方觀察）：
- [項目：簡述 + 為何需要對方判斷]
（若無，寫「無跨區議題，仍請例行掃描」）

**建議對方掃描重點**：
- [方向：為何可能有問題]

**請你回報**：
依本檔 Section 7 產出報告，第 5 段反向委託回本方（若有跨區議題）。

**本方近期已完成**（避免重工）：
- [PR #XXX]
```

目的：Kai 複製此段貼給對方 → 對方啟動同步掃描 → 閉環。

---

## 8. 紀律要求

- 不要為了顯得全面而把很多項目都說得很重要
- 不要平均分配注意力，請真的排序
- 不要回頭重講已處理過的表層問題
- 不要硬補低槓桿建議
- 若真正問題在更上游，請直接指出
- 若某些部分不是瓶頸，請直接降級優先級
- 每個建議必須有 Owner + Blocking 標記
- 缺少任何必填欄位 → 報告不完整，需補齊

---

## 觸發方式（唯一口令）

觸發詞：**`掃描`** 或 **`/scan`**（Claude Code 原生 slash command）。

| Kai 說 | 代理動作 |
|--------|---------|
| `掃描` 或 `/scan` | 讀本檔 → 掃描自己責任區 → 產出 4 段報告 |
| `掃描 全修` 或 `/scan full-fix` | 掃描 → 產出 Top3 → 直接執行全部修改（依下方全修規則） |

> Claude 側：`.claude/commands/scan.md` 為原生 skill wrapper，引用本檔。
> Codex 側：直接讀本檔（`docs/contracts/agent-collaboration.md`）執行。

---

## 格式守門（掃描報告完成標準）

兩項必產出：
- [ ] **Top3**（每項含 Owner + Blocking）
- [ ] **同步掃描委託**（✂️ 可複製段）

其他面向（判讀、取捨、下一步）可合併濃縮。Kai 回覆「不符合憲章格式，重交」→ 代理補齊必產出項。

---

## 全修執行規則（`掃描 全修` 時適用）

掃描完成後，直接進入修改。不要只給建議。

### 執行紀律

1. 直接修改程式碼/文件
2. 跑完所有驗證：lint / test / cross-file checks
3. 修掉全部錯誤
4. 反覆驗證，直到全部 100% 通過
5. 沒有通過驗證，不准視為完成
6. 不要長時間累積大量未驗證修改
7. 一次只處理一個最小可完成單位：修改 → 驗證 → 修正 → 通過 → 再下一步
8. 若任務過大，主動拆成可安全提交的小步驟
9. 若卡住或不確定，先停止新增修改，先回報目前可提交邊界
10. 任何時候都不要讓 branch 處於「改了很多，但不能安全 commit」的狀態

### 每次回報必須包含

```
目前狀態：
- 已完成：
- 進行中：
- 未開始：
- 卡點：
- 是否已可安全 commit：是 / 否
- 是否已同步 remote：是 / 否
```

### 最終回報必須包含

- 修改檔案
- 修改內容
- 驗證結果
- 剩餘問題（若有）

### 補充要求

- 不要只說「正在處理」「快好了」，明確說出做到哪一步
- 若某一步尚未驗證通過，直接標示
- 若需要停止，說清楚哪些已完成、哪些未完成、哪些已可安全 commit
- 收尾前確認修改已具備可提交條件

---

## 9. Claude × Codex 協作 SOP

> version: 1.0 | last_updated: 2026-04-15

### 核心原則

**一次只有一邊在改同一批檔案。**

### 標準流程

```
Codex 做事 → push 到 codex/* 分支 → 任一代理開 PR
  → Claude fetch + merge 解衝突 → push 回原分支 → Kai 按 Merge
```

| 步驟 | 誰做 | 做什麼 |
|------|------|--------|
| 1 | Kai | 給 Codex 任務 |
| 2 | Codex | 在 `codex/*` 分支改 code → pytest + ruff → push |
| 3 | Kai / Claude / Codex | 任一方開 PR（誰手上就誰開）|
| 4 | Claude | `git fetch` → 在 `codex/*` **原分支**追加 commit 解衝突 / 驗證 → push |
| 5 | **Kai（唯一）** | 在 GitHub 按 Merge |

**紀律**：merge 一律 Kai 決定時機，代理不自行 merge。

### 責任區（不重疊）

> **v1.7+ 已硬化**：違反下表即 `.github/workflows/territory-lint.yml` CI red、PR block。例外：PR body 明寫 `territory override justified by: <原因>` 由 Kai 人工放行。對應 CLAUDE.md 禁令 #8。

| 區域 | Owner | 對方角色 |
|------|-------|---------|
| `scripts/ops/**`, `scripts/utils/**`, `scripts/lint/**`, `tests/**` | **Codex** | Claude 不碰，只驗證 |
| `02-skill-factory/**`, `.claude/**`, `CLAUDE.md`, `01-data-brain/**`, `03-production-line/**`, `07-changelog/**` | **Claude** | Codex 不碰 |
| `docs/contracts/**` | **共享但單向輪替** | 每輪只能一邊改、PR 描述必須標 Owner；另一方同輪改同檔 → 自動 reject、請 rebase 掉對方改動 |
| `data/**/*.json`（pipeline、patterns 等） | **CLI 寫入（雙方皆可）** | 工具碼 `scripts/ops/` 屬 Codex；資料層透過 `video-ops.py` CLI 操作、不手動改 JSON |
| `.github/workflows/**`, `engine-manifest.json`, `README.md` | **共享** | 單向輪替、PR body 標 Owner |

### 跨區規則

- 必須跨區時：先問 Kai「對方有在改這個檔案嗎？」
- 確認沒有才動手
- **絕不兩邊同時改同名檔案**

### Codex 無法 push 時的替代方案

1. Kai 告訴 Claude「Codex 改了 X，但 push 不了」
2. Claude 根據描述自行實作
3. **不建同名檔案** — 用不同檔名或在現有檔案追加
4. 未來 Codex 能 push 後，以 Codex 版本為準合併

### 救援規則（Codex rebase 失敗 / push 失敗）

Claude 介入救援時：

1. **在 `codex/*` 原分支追加 commit**，不另開平行 `claude/*` 分支
2. 例外：若 Codex 分支狀態已無法修復（如 rebase 污染主線）→ 才開 `claude/codex-<task>-rescue-N` 並 cherry-pick Codex 新增、拒絕所有退回
3. 救援 PR 描述需標「救援第 N 次」+ 列出拒絕的 Codex 退回項
4. Codex 下次若要追加、須先 fetch 最新 main，不從舊 base rebase

### Codex 任務 prompt 模板（v1.3 新增、v1.9 加 Pre-flight territory check + Action location）

**Claude 撰寫給 Codex 的任務時、prompt 頂部必須含此 base-check 前綴 + 通過 territory pre-flight check + 動作位置必明示**。這是唯一對 AI agent 有約束力的防呆層（agent 讀 prompt、不一定讀 repo markdown）。

根因（v1.3）：PR #179 是 Codex 第 6 次從老 base rebase（`24e9611`、落後 main 11 個 commit）。契約 §救援規則 point 4 早寫「須 fetch 最新 main」、但 Codex 未執行 → 必須改由任務 prompt 強制執行。

根因（v1.9、L-0021）：2026-04-26 PR #327/#328 連續觸發兩種錯：
- **Territory 違規**：Claude task prompt 寫「engine_version 5.52 → 5.54 + 加 CHANGELOG v5.54 entry」、Codex 照做、territory-lint fail（CHANGELOG 屬 Claude 領土、不在 CODEX_OK）。Codex 沒錯、Claude task prompt 設計錯。
- **動作位置誤判**：Claude 對 Codex 說「PR body 補一行 territory override」、Codex 解讀為「開新 PR + 把 override 寫進 CHANGELOG 內文」（PR #328）。Codex 預設選「開新 PR」、未明示否決就會跑這條。

#### 必須前綴（複製到任務最上方）

```
# 0) 開工前（必做、先回報後才開始改動）

# 若 sandbox 無 origin remote、看 HEAD 是否已對；對了就放行、不對就停
if ! git rev-parse origin/main >/dev/null 2>&1; then
  CURRENT=$(git rev-parse --short HEAD)
  TARGET="<本任務指定的 main sha>"
  if [ "$CURRENT" = "$TARGET" ]; then
    echo "✅ no origin but HEAD matches target"
    git checkout -b codex/<task-name>
  else
    echo "❌ no origin and HEAD=$CURRENT != $TARGET"
    exit 1
  fi
else
  git fetch origin main
  git checkout -B codex/<task-name> origin/main
fi
git rev-parse --short HEAD   # 回報此 base sha

# 1) 若 base sha ≠ 本任務指定的 main sha（見下方）→ 停止、任務作廢、
#    重開新分支、回報基底不符。不得在舊 base 上改動。

# 1.5) 任務指令含模糊動作詞（"補一行" / "修一下" / "處理" / "澄清" 等）→
#      停下、不要 push 任何 commit、改在現有 PR 留 comment 回問 Kai 確認動作位置：
#         「請問 X 是要：(a) edit PR #N body / (b) 修檔案 Y 第 Z 行 /
#                       (c) 開新 PR / (d) 不改 PR、只回 comment？」
#      Kai 回覆後再執行。預設選「開新 PR」是常見的解讀錯（L-0021 / PR #328 反例）。

# 2) 改完後回報：
git rev-parse --short HEAD            # head sha
git log --oneline -n 5 --decorate     # 最後 5 commit
```

#### Pre-flight territory check（v1.9 新增、L-0021 對應）

**Claude 寫 Codex task prompt 之前必跑**：把 task 中所有要求 Codex 修改的 paths 列出、對照 §9.3 CODEX_OK regex。任何不在 CODEX_OK 的 path（如 `07-changelog/CHANGELOG.md` / `01-data-brain/brand.md` / `.claude/**` / `02-skill-factory/**` / `CLAUDE.md`）必擇一處理：

| 選項 | 何時用 | 做法 |
|------|-------|------|
| **(a) 拆 follow-up**（預設）| Claude 領土改動可後做 | task prompt 只給 Codex 領土改動、Claude PR merge 後跟一支 follow-up commit 補 Claude 領土的關聯改動（如 CHANGELOG 條目） |
| **(b) 預授 override** | engine bump + CHANGELOG 同 PR 慣例必須維持 | task prompt 明示要 Codex 在 PR body 加 `territory override justified by: <原因>`（§9.5 救援規則）|

**反例**：L-0021、PR #327。task prompt 寫「engine_version 5.52 → 5.54 + 加 CHANGELOG v5.54 entry」、未拆 follow-up、未預授 override → Codex 做完 territory-lint fail。

#### Action location must be explicit（v1.9 新增、L-0021 對應）

當 Claude 給 Codex 的任務含「修改某個 PR」「修 CI 失敗」「補 X」等指令時、**必明寫動作位置**。Codex 預設選「開新 PR」、不明示否決就會跑這條。

| Claude 想表達 | 必寫法 | 不要寫 |
|-------------|-------|-------|
| 編輯既有 PR 的 metadata | `edit PR #N body`（明寫 PR 號 + body） | 「補一行 territory override」（Codex 會猜成開新 PR）|
| 修檔案 X | `修 <絕對 path>` + 在哪一行 + 加 / 改 / 刪 | 「修 X」（Codex 可能改錯位置）|
| 開新 PR | `開新 PR、branch 名 codex/<...>` | 任意「處理一下」（Codex 預設開新 PR、即便不該）|
| 不改 PR、只補資訊 | `回覆 PR #N comment、不要 push 任何 commit` | 「澄清一下」（Codex 會 push）|

**反例**：L-0021、PR #328。Claude 對 Codex 說「PR body 補一行」、未明寫「edit PR #327 body」→ Codex 開新 PR + 把 override 寫進 CHANGELOG 內文 + 又改 CHANGELOG（再次 territory 違規）。

#### Claude 側紀律（CLAUDE.md 禁令 #6 對應）

- 每次生成給 Codex 的任務前、先跑 `git rev-parse --short origin/main` 取得當下 main sha、寫進任務中「本任務指定的 main sha」欄位
- 任務 body 最上方必附此 base-check bash（含 sandbox no-origin fallback、v1.9+）、不得省略
- 任務 body 必含 territory pre-flight check + action location 明示（v1.9+）
- Codex 回報的 base sha 若不符 → Kai 立刻中止該輪、不等 PR
- Codex 觸發 territory-lint fail → 99% 是 Claude task prompt 漏了 pre-flight check、不是 Codex 的錯

#### Codex 側紀律

- 不執行步驟 0 即視為違反契約
- base sha 不符就繼續改 → 下輪 Claude 直接救援 cherry-pick、退回項全拒
- 收到任務時、若指令含模糊動作位置（「補一行」「修一下」「澄清」）→ 主動回問 Kai 確認、不要預設開新 PR


### 版本協調（engine_version / CHANGELOG）

engine_version bump 與 CHANGELOG 最新條目**天然跨代理衝突**（兩邊改不同東西都會動到）。規則：

1. **PR 描述寫預計版號**，但不是承諾
2. **以 merge 順序為準** — 先 merge 方佔用該版號
3. **後 merge 方** 負責 rebase + bump 下一個版號 + 調整 CHANGELOG 位置（新版在上）
4. 若兩個 PR 同時開著、Kai 指定誰先 merge → 另一方立刻 rebase，不等 CI
5. 不接受「跳號」（4.26 → 4.28 skipping 4.27）除非前版 PR 已關閉

### 分支命名

| 來源 | 格式 | 範例 |
|------|------|------|
| Claude | `claude/*` | `claude/add-new-skill-PIrkh` |
| Codex | `codex/*` | `codex/outline-codex-collaboration-plan` |

### 合併後清理

PR merge 後，刪除遠端分支（GitHub 垃圾桶圖示或 `git push origin --delete <branch>`）。
下一輪任務請重新開新分支，不重用舊分支。

### Sync Report 規格

Claude ↔ Codex 的同步報告至少包含：
- Branch 與 latest commit
- 已合併內容摘要
- 衝突解決決策（保留哪一版、原因）
- 對方下一步注意事項

收到 Sync Report 後，先以本檔為準同步流程規則，再開始下一次改動。

### 反向委託閉環（scan 第 5 段）

`/scan` 新格式（Section 7）規定每份報告必須含「第 5 段：給對方代理的同步掃描委託」。
啟動閉環流程：

| 步驟 | 誰做 | 做什麼 |
|------|------|--------|
| 1 | 本方代理 | 跑 `/scan` → 產出 5 段報告（第 5 段為給對方的 prompt） |
| 2 | Kai | 複製第 5 段「✂️」區塊，貼給對方代理 |
| 3 | 對方代理 | 收到請求 → 對自己責任區跑 `/scan` → 產出 5 段報告 |
| 4 | 對方代理 | 第 5 段「反向委託」回本方（若有跨區議題）或寫「無跨區議題」 |
| 5 | Kai | 複製回覆第 5 段 → 貼回本方 → 若有新跨區議題進一輪；否則閉環結束 |

**閉環目標**：雙方在同一認知基線。避免「一方掃完後另一方繼續停在舊認知」。

**跨區任務執行原則**：
- Claude 側跨區議題（Codex 責任區發現的問題）→ 由 Claude 在第 5 段標記，Codex 收到後判斷處置
- Codex 側跨區議題（Claude 責任區發現的問題）→ 由 Codex 在第 5 段標記，Claude 收到後判斷處置
- **不代工**：Claude 不改 Codex 責任區程式；Codex 不改 Claude 責任區 content/skill

### PR 描述最小集

每個 PR 描述至少包含：
- 改動範圍（檔案/模組）
- 測試結果（指令 + 結果）
- 是否涉及共享區（`docs/contracts/**`）

---

### §9.11 Cross-territory engine bump 規則（v1.8+、解 #271/#272 rescue deadlock）

**規則**：Codex PR **不自行 bump `engine_version`**。由 Claude 側同步開「**配對 CHANGELOG PR**」處理版號 + entry。

**為什麼**：`engine-version-check` 要求 engine bump 必對應 CHANGELOG entry、但 CHANGELOG 是 Claude 領土（territory-lint 硬化擋）、Codex 無法自補。Codex 若自行 bump engine、就卡死需 rescue（#271 事故模式）。

**執行**：
- Codex PR：改 contract file（`docs/contracts/**`）+ 對應 code、**不動** `engine-manifest.json._meta.engine_version`
- Claude 配對 PR：bump engine + CHANGELOG entry + manifest 對應檔版本列（例 `docs/contracts/video-ops-cli.md: "1.11" → "1.12"`）
- Merge 順序：**Claude 配對 PR 先 merge**（engine + CHANGELOG 先到位）→ Codex PR rebase → `engine-version-check` 自動 pass（Codex 只改 contract file 內容、沒動 engine、就不觸發 check 擋）

**例外**（允許 Codex 自己 bump engine）：
- 純 Codex 領土檔案（`scripts/**` / `tests/**`）有跨客戶 engine 性質改動
- PR body 明寫「no CHANGELOG needed: internal-only scope」
- 觀察：2026-04-24 後未遇此情境、暫視為 edge case

### §9.12 Codex task base check 強制（v1.8+、解 #276 stale base 重做）

**規則**：Codex task brief 頂部**必**含 base check、任務執行前**必**跑、結果**必**記入 PR body。

**執行**：
- Brief 頂部必有 block：
  ```bash
  git fetch origin main
  ORIGIN_MAIN=$(git rev-parse --short origin/main)
  echo "origin/main: $ORIGIN_MAIN"
  python3 -c "import json; m=json.load(open('engine-manifest.json')); print('engine:', m['_meta']['engine_version'])"
  ```
- Codex PR body 必記錄：`Base verified: origin/main @ <sha>` + `Engine version observed: <X.Y>`
- **engine 落後當時最低門檻 → 立刻 STOP、不要在舊 base 動手**

**為什麼**：#276 事故 — Codex 用 3 輪前的 stale base（engine 5.23、落後 3 版）重做、90% 重複 main 已有的 #271 內容、最後被 close。**老舊 base + 任務重做 = duplicate noise**。

**例外**：sandbox fetch 失敗（如 Codex Cloud 無 origin remote）→ 可暫用 local HEAD、但必在 PR body 誠實記錄「Base verified: unavailable（sandbox limitation）」。此時由 Kai / Claude 在 merge 前人工驗證 diff vs 最新 main。

---

**一句話：Codex 改 code、Claude 改 content/skill、Kai 按流程切換；同名檔案不並行修改。**

---

## 10. 跨區議題紀錄（Active）

### 2026-04-20：skill-memory 三 JSON 合併為 lessons.json（L3 重設計）

**背景**：Opus 4.7 視角重新檢查後，三個 skill-memory JSON（`claude-mistakes.json` / `generation-rules.json` / `script-deviations.json`）本質是同一件事——「下一輪生成要避開 / 要學會的東西」——合併為單一 `lessons.json`，用 `origin` 保留來源、`stage` 取代三檔各自的畢業邏輯。

**契約**：
- 新契約：`docs/contracts/lessons-schema.md` v1.0

**責任切分**：
| 區塊 | Owner | 動作 |
|------|-------|------|
| `scripts/ops/lib/lessons.py`（新） | Codex | 實作 load / save / add / promote_stage / query |
| `scripts/ops/lib/migrate_lessons.py`（新、一次性） | Codex | 三檔合併 + rename `.legacy.json` |
| `scripts/ops/lib/mistakes.py` / `deviations.py` / `sedimentation.py` | Codex | 寫入路徑改指向 lessons |
| `scripts/ops/video-ops.py`（記錯 / diff-script / auto_extract CLI） | Codex | 寫 lessons.json 而非老三檔 |
| `data/kai/lessons.json`（新） | Codex | 由 migration 生成 |
| `data/skill-memory/*.legacy.json` | — | v4.76 已清除（比計畫提前、migration 驗證後刪） |
| `tests/test_lessons.py`（新） | Codex | CRUD + migration round-trip |
| `tests/test_mistakes_archive.py` / `test_deviations.py` | Codex | 改指向新 API 或標 legacy |
| `02-skill-factory/flow-operator/SKILL.md` 步驟 0 | Claude | Codex 完成後改載入清單（1.37 → 1.38）|
| `01-data-brain/index.md` 知識儲存分工表 | Claude | 同上時機更新 |
| `CLAUDE.md` 資料地圖 | Claude | 同上時機更新（4.5 → 4.6 如需要）|

**互不侵入**：
- Codex **不改**：`.claude/**`、`02-skill-factory/**`、`01-data-brain/**`、`CLAUDE.md`
- Claude **不改**：`scripts/ops/**`、`tests/**`、`data/**/*.json`

**engine_version 協調**：Claude 側 PR 先 bump 至 4.35（L4 + L2 + L3 前置契約）。Codex 側 PR 預計 bump 至 4.36，merge 前若 Claude 有新 PR 已佔 4.36 → Codex rebase 至 4.37。
