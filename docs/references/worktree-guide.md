# Git Worktree 指引

> version: 1.0 | last_updated: 2026-04-19
> 按需載入：同時動多個分支 / 多個 repo 時讀。
> 核心原則：**同一 repo 多個實體目錄，每個目錄一個分支，互不干擾。**

---

## 為什麼

目前踩過的問題：

- PR #146 #147 #148 #150 都重用同名分支 `claude/good-morning-MXI78`、`claude/engine-tools-rescue`，造成 GitHub branches view 混亂
- 一次只能在一個分支工作；切分支會動 working tree，中途有未 commit 改動就卡
- 未來 LONGBRO 加入後，會同時需要動引擎 repo + 客戶 repo

Worktree 解法：**同一 repo 複製成多個實體目錄**，每個目錄固定一個分支，不用切、不互相蓋。

---

## 基本用法

### 新增 worktree

```bash
cd /home/user/KaiOS-ContentSystem

# 為新 feature 建 worktree（自動建新分支）
git worktree add ../KaiOS-boris-opts -b claude/boris-optimizations

# 切過去工作
cd ../KaiOS-boris-opts
# ... 改檔案 / commit / push ...
```

結果：
```
/home/user/
├── KaiOS-ContentSystem/           ← main 分支（本主目錄）
├── KaiOS-boris-opts/              ← claude/boris-optimizations
└── KaiOS-another/                 ← 另一個 feature
```

三個目錄共用同一個 `.git/`，但 working tree 各自獨立。

### 列出所有 worktree

```bash
git worktree list
```

### 移除 worktree（不刪分支）

```bash
cd /home/user/KaiOS-ContentSystem
git worktree remove ../KaiOS-boris-opts
```

### 移除 worktree + 刪分支

```bash
git worktree remove ../KaiOS-boris-opts
git branch -D claude/boris-optimizations
git push origin --delete claude/boris-optimizations
```

---

## 使用時機

### ✅ 該用

- **同時管多個 feature**：例如正在做引擎升版 + 同時想跑客戶回填，不想互相干擾
- **長時間運行的 feature**：某分支要等 Codex review / CI 跑完，這段期間繼續在別處工作
- **多 repo 協作**：LONGBRO / 其他客戶 repo 加 `git remote` 之後，用 worktree 同時管引擎 repo 和多個客戶 repo

### ❌ 不用

- 單純想切分支看看：`git checkout` 就夠
- 短任務（< 30 分鐘）：開 worktree 的設置成本不划算
- 還沒 push 的臨時分支：直接 `git stash` 更快

---

## 命名慣例

Worktree 目錄用短前綴：

| 用途 | 目錄名範例 |
|------|---------|
| Feature 開發 | `KaiOS-<feature-slug>` |
| 客戶 repo 協作 | `KaiOS-Client-LONGBRO`（若 LONGBRO 是獨立 repo）|
| 回填 / 生產 | `KaiOS-daily-prod`（長駐 main）|

不要跟主目錄 `KaiOS-ContentSystem` 同名。

---

## 常見坑

| 問題 | 解法 |
|------|------|
| worktree 刪目錄後 `git worktree list` 仍顯示 | `git worktree prune` 清幽靈記錄 |
| 兩個 worktree 同時改同檔 | git 會阻擋其中一方 commit（同分支會報錯，不同分支各自 commit 沒問題）|
| hooks 不生效 | hooks 存在 `.git/hooks/`，共用；`.claude/hooks/` 是 repo 檔案，自動跟著 working tree |
| Worktree 目錄裡跑 `pytest` 路徑問題 | 大部分腳本用 `CLAUDE_PROJECT_DIR` 或相對路徑就沒事，若有寫死絕對路徑要小心 |

---

## 何時該換主目錄

主目錄（`KaiOS-ContentSystem`）固定停在 main。所有 feature 都在 worktree。這樣：

- main 主目錄永遠乾淨，可以當 fresh reference
- Feature 完成後 worktree remove 就好，主目錄零影響
- 多個 PR 同時掛著、不互相搶 working tree

如果主目錄長期停在某 feature 分支而不是 main，代表你**沒在用 worktree**——流程退化回舊模式。
