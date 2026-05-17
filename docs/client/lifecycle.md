# 客戶 repo 生命週期 SOP

> version: 1.2 | last_updated: 2026-04-23
> 給未來 Kai 自己看的操作手冊。新接客戶、持續維運、同步引擎三件事。

---

## 客戶類型

| 類型 | 所屬 GitHub 帳號 | 使用情境 |
|------|----------------|---------|
| **類型 1：Kai 帳號下** | `pei760730/KaiOS-Client-XXX` | Kai 自己代管，客戶不直接操作 GitHub |
| **類型 2：客戶 Gmail 帳號** | `customer-gmail/KaiOS-Client-XXX` | 客戶有專屬感、Kai 不掌管客戶帳號 |

兩種類型的流程在「初始化」階段有差異，**日常生產**和**同步引擎**完全一樣。

---

## 三個核心流程

### 流程 A：接新客戶（30 分鐘完成）

```
1. GitHub「Use this template」 → 新 repo
2. clone → 跑 bootstrap-client.sh
3. git push
4. 開始「填大腦」
```

### 流程 B：客戶日常生產

跟 Kai 現在一樣：`丟靈感` / `確認要拍` / `存檔` / `上線` / `回填`。

### 流程 C：定期同步引擎

```
1. 在客戶 repo 的 Claude Code 打「/sync-engine」
2. 看計畫、確認、同步、驗證、commit+push
```

---

## 流程 A 詳細：接新客戶

### 前置條件（A repo 一次性設定，做過一次不用再做）

1. 在 GitHub `pei760730/KaiOS-ContentSystem` → **Settings** → 勾選「**Template repository**」
2. 確認 A repo 根目錄有 `01-data-brain/template/`、`data/template/`、`scripts/bootstrap/` 三個東西

### Step 1：GitHub 建新 repo（1 分鐘）

1. 打開 `https://github.com/pei760730/KaiOS-ContentSystem`
2. 點右上角綠色按鈕「**Use this template**」→「Create a new repository」
3. 填：
   - Owner: `pei760730`（類型 1）
   - Repository name: `KaiOS-Client-{品牌代號}`（例 `KaiOS-Client-LongBroOS`）
   - ✅ Private
4. 「Create repository」

### Step 2：clone 到本地（1 分鐘）

```bash
git clone https://github.com/pei760730/KaiOS-Client-LongBroOS.git
cd KaiOS-Client-LongBroOS
```

### Step 3：跑 bootstrap（5 分鐘）

```bash
bash scripts/bootstrap/bootstrap-client.sh \
  --operator longbro-os \
  --brand "長兄 OS"
```

腳本會：

1. **刪除**原引擎實例（Kai 紅茶巴士）資料：
   - `01-data-brain/brand.md` / `cases.md` / `transcripts/`
   - `data/kai/` / `data/employee-backup/`
   - `03-production-line/02-ready-to-shoot/kai/`、`03-done/kai/`
   - `00-control-center/todo/*.md`

2. **建立**空白客戶架構：
   - `01-data-brain/brand.md` / `cases.md`（從 `template/` 複製空殼）
   - `data/longbro-os/pipeline.json` / `performance-patterns.json`
   - `03-production-line/02-ready-to-shoot/longbro-os/`、`03-done/longbro-os/`

3. **替換品牌名**：`Red Tea Bus` / `紅茶巴士` → `長兄 OS` 在 CLAUDE.md / README.md / brand.md / cases.md

4. **更新 config.py**：
   - OPERATORS 加入 `longbro-os`
   - `DEFAULT_OPERATOR = "longbro-os"`

5. **記錄初始化資訊**到 `engine-manifest.json`：
   ```json
   "_meta": {
     "client": {
       "brand": "長兄 OS",
       "operator": "longbro-os",
       "initialized_at": "2026-04-18",
       "initialized_from_engine_version": "4.9"
     }
   }
   ```

6. **跑驗證**：pytest + validate-all。若 fail 會提醒 Kai。

### Step 4：推到 GitHub（1 分鐘）

```bash
git add -A
git commit -m "Initialize client: 長兄 OS (operator longbro-os, from engine v4.9)"
git push -u origin main
```

### Step 5：設定 engine remote（一次性，為了未來 /sync-engine）

```bash
git remote add engine https://github.com/pei760730/KaiOS-ContentSystem.git
git fetch engine main
```

### Step 6：開始填大腦（20+ 分鐘）

打開 Claude Code，說：「填大腦」→ Claude 引導你填 `01-data-brain/brand.md` 的 [0]~[12]。

**最小可用**：先填 brand.md [0] [1]（基本資料、業務能力與優勢）+ personas/kai.md [1]（說話風格），就可以開始「丟靈感」。

**brand.md 的特殊角色**（v4.62+）：每次新對話由 `.claude/hooks/session-start.sh` 自動注入 Claude context 全文、讓 Claude 啟動就帶完整大腦。填好後效果立竿見影。

---

## 流程 A 替代版（類型 2）：接客戶 Gmail 帳號的 repo

客戶擁有自己的 GitHub repo（他自己的 Gmail 帳號下），要求專屬感、完全自有資料。

### 前置條件

- 客戶已建一個**空的 GitHub repo**（在他自己的 Gmail 帳號下），例如 `customer-gmail/KaiOS-Client-BrandX`
- Kai 有短暫的寫入權限（客戶臨時加 Kai 為 collaborator，初始化完成後可移除）
  - 或：Kai 拿到 client repo 的 push URL + PAT，在自己 sandbox 初始化後 push 回去

### Step 1：在 Kai 的 Claude Code 裡 clone 引擎（不用客戶 repo）

```bash
git clone https://github.com/pei760730/KaiOS-ContentSystem.git KaiOS-Client-BrandX
cd KaiOS-Client-BrandX
```

### Step 2：切掉原 origin、指向客戶 repo

```bash
git remote remove origin
git remote add origin https://github.com/customer-gmail/KaiOS-Client-BrandX.git
```

### Step 3：跑 bootstrap（跟類型 1 一樣）

在 Claude Code 裡說「初始化新客戶：品牌 BrandX、operator 代號 brandx」，或直接：

```bash
bash scripts/bootstrap/bootstrap-client.sh --operator brandx --brand "BrandX"
```

### Step 4：push 到客戶 repo

```bash
git add -A
git commit -m "Initialize client: BrandX"
git push -u origin main
```

### Step 5：設定 engine remote 給客戶（他未來用 /sync-engine 會需要）

```bash
git remote add engine https://github.com/pei760730/KaiOS-ContentSystem.git
git fetch engine main
```

### Step 6：交接給客戶

- 告訴客戶這 repo 的用法（可以複製 `docs/client/lifecycle.md` 的「流程 B 客戶日常生產」和「流程 C 同步引擎」給他）
- 若你是暫時 collaborator → 請客戶移除你的權限（除非要長期代管）
- 若用 PAT push → 移交後請客戶 revoke 你的 PAT

### 類型 2 的注意事項

- **引擎 repo 必須 public**（或客戶帳號有讀權限），客戶的 `/sync-engine` 才能從 A 拉更新
  - 若 A repo 想保持 private → 要給客戶 read-only collaborator 權限
  - 長期最優解：建 `pei760730/KaiOS-Engine` public 子 repo 自動從 A 同步「引擎部分」（不含 Kai 紅茶巴士資料），客戶從這個 public engine 拉更新 — **這部分工具未做**，目前類型 2 只能走「A 加 read-only collaborator」或「保持 A public」
- 客戶自行填入的大腦內容（brand.md / cases.md / pipeline.json / 腳本）永遠不會回流到 A

---

## 流程 C 詳細：同步引擎

### 何時跑

- 每月月底固定一次
- A 有緊急 bug fix 時立刻跑
- 從 `pei760730/KaiOS-ContentSystem` 的 CHANGELOG 看到 🚨 記號時盡快跑

### 步驟

1. 進客戶 repo 目錄，開 Claude Code
2. 打：`/sync-engine`
3. Claude 會：
   - `git fetch engine main`
   - 比對兩邊 `engine-manifest.json`
   - 讀 CHANGELOG 差異
   - 列出同步計畫給你看
4. 你看計畫 → 說「同步」
5. Claude：
   - 從 engine/main 覆寫引擎檔（不碰客戶資料）
   - 跑 pytest / lint / validate
   - commit + push

### 驗證過不去怎麼辦

Claude 會停在「驗證失敗」階段不 commit。
- 常見原因：引擎版的 schema 改了，客戶 pipeline.json 需要 migration
- 處理：Claude 會建議跑 `python scripts/ops/video-ops.py migrate --auto-migrate`，或人工處理
- 修掉後再次 `/sync-engine` 就會從驗證階段繼續

---

## 客戶 repo 命名規範

| 類型 | 命名 | 範例 |
|------|------|------|
| 引擎 repo | `KaiOS-ContentSystem` | 不動 |
| 客戶 repo | `KaiOS-Client-{品牌英文代號}` | `KaiOS-Client-LongBroOS` / `KaiOS-Client-BrandX` |
| operator 代號 | 全小寫字母 + 連字號 | `longbro-os` / `brandx` |

**避免**：
- 中文（路徑會出事）
- 底線 + 連字號混用
- 大小寫混用（Windows 不區分 case 會撞車）

---

## 客戶 repo 裡有但不該進 engine 的檔案

bootstrap 後，**客戶資料**不會回流到 A。列表（同時也是 `/sync-engine` 絕不覆蓋的清單）：

- `01-data-brain/brand.md` / `cases.md` / `transcripts/`
- `data/{operator}/*.json`
- `data/{operator}/lessons.json`（客戶學習紀錄、v4.36 起取代 `data/skill-memory/*.json` 三檔）
- `03-production-line/02-ready-to-shoot/{operator}/*`
- `03-production-line/03-done/{operator}/*`
- `00-control-center/todo/*`

---

## 萬一出事怎麼救

### 情境 1：bootstrap 跑壞，客戶 repo 爛掉
- 因為剛 clone 沒資料，直接**刪 repo 重來**最乾淨
- 或 `git reset --hard HEAD` 回到 bootstrap 前

### 情境 2：/sync-engine 把客戶資料蓋掉了
- **不會發生**，sync-engine 只動 `engine-manifest.json` 裡 version 不為 null 的檔案
- 若真的發生 → `git log` 找到 sync commit → `git revert` 或 `git reset` 回前一版

### 情境 3：客戶 repo 跟 engine 版本差太遠
- 超過 3 個大版本 → 不要直接跑 /sync-engine
- 先看 A 的 CHANGELOG v{客戶} 到 v{最新} 有沒有 schema breaking change
- 有的話要逐版同步，不跨版

---

## 反向同步：客戶好用的功能回流到 A

如果客戶 B repo **自己改了某個 skill 很好用**，要回流到 A：

1. 在 B 裡 export 改動 → `git diff engine/main -- 02-skill-factory/xxx/SKILL.md`
2. 手動複製到 A 的同路徑
3. 在 A 升版（SKILL.md heading + frontmatter + stub + README + CHANGELOG）
4. A 推到 main
5. 所有客戶下次 /sync-engine 時會拿到
