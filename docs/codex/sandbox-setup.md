# Codex Sandbox 一勞永逸配置（給 Kai）

> 讓 Codex Cloud sandbox 每次 session 都自動有 gh CLI + GitHub auth + git remote，
> 終結「Codex 做完 push 不了 → Claude 代工 → 重複踩 base 太舊」的循環。

---

## 為什麼需要這個

過去三輪 Codex 交付（PR #128、#134、#136）都犯同樣錯：
- 他的 sandbox 沒 gh CLI
- 沒設定 git remote origin
- 沒 auth token
- 結果他 push 失敗或 push 到錯的分支 → base 過舊 → Claude 要 cherry-pick 替代

配置好後：
- Codex 能自己 `gh pr create` / `gh pr comment` / `git push origin --delete`
- 他的 commit 一定基於最新 main（init script 自動 fetch）
- Claude 不再需要代工 fallback

---

## 流程概覽（三步）

1. **Kai 在 GitHub 生一個 Fine-grained Personal Access Token (PAT)**
2. **Kai 在 Codex Cloud 平台設 Secret + Init Script**
3. **驗證：叫 Codex 跑一行指令看輸出**

預計 30-60 分鐘完成。

---

## Step 1：生 GitHub Personal Access Token

1. 登入 https://github.com/settings/tokens?type=beta
2. 點綠色 **Generate new token**
3. 填：
   - **Token name**：`codex-cloud-auto-push`
   - **Expiration**：建議 **1 year**（到期前 GitHub 會提醒 Kai 續期）
   - **Repository access**：選 **Only select repositories** → 勾 `pei760730/KaiOS-ContentSystem`
4. **Repository permissions**：

| 權限 | 設定 | 理由 |
|------|------|------|
| Contents | **Read and write** | push commits、刪分支 |
| Pull requests | **Read and write** | 開 PR、close PR、留 comment |
| Issues | **Read and write** | 必要時開 issue |
| Metadata | Read-only（自動） | 讀 repo 基本資訊 |

其餘權限保持預設（none）。

5. 按 **Generate token**
6. **立刻複製 token**（只顯示一次），形如 `github_pat_11ABCDE...`

> ⚠️ **Token 管理**：這組 token 只存在 Codex Cloud 的 Secret store，不貼給任何人、不放進 repo。若懷疑洩漏立刻到 GitHub 按 **Revoke**。

---

## Step 2：Codex Cloud 平台設定

### 2a. 設 Secret

具體位置因平台介面而異。在 Codex Cloud 設定頁找：
- **「Secrets」** / **「Environment variables」** / **「Workspace secrets」**

新增一個：
- **Name**：`GITHUB_TOKEN`
- **Value**：Step 1 複製的 token（`github_pat_...`）
- **Scope**：applies to all tasks / workspace-wide

儲存。

### 2b. 設 Init Script（Workspace Bootstrap）

找：
- **「Workspace init」** / **「Setup command」** / **「Bootstrap script」** / **「Dev container setup」**

貼以下內容：

```bash
#!/bin/bash
# Codex Cloud workspace init — 每次 sandbox 啟動自動執行
set -e

# 1. 裝 gh CLI（GitHub CLI）
if ! command -v gh &>/dev/null; then
  echo "📦 Installing gh CLI..."
  (type -p curl >/dev/null || apt-get update && apt-get install -y curl) > /dev/null
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
  chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update > /dev/null && apt-get install -y gh > /dev/null
fi

# 2. GitHub auth（從 GITHUB_TOKEN secret）
if [ -n "${GITHUB_TOKEN:-}" ]; then
  echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null || true
  gh auth setup-git 2>/dev/null || true
fi

# 3. 設 git remote origin（確保指向正確 repo）
if [ -d ".git" ]; then
  if ! git remote -v | grep -q "pei760730/KaiOS-ContentSystem"; then
    git remote remove origin 2>/dev/null || true
    git remote add origin "https://${GITHUB_TOKEN}@github.com/pei760730/KaiOS-ContentSystem.git"
  fi
  # 自動拉最新 main，避免 base 太舊
  git fetch origin main 2>/dev/null || true
fi

# 4. 設 git user identity（Codex 預設是 "Codex <codex@openai.com>"，改成 Kai）
git config --global user.name "pei760730"
git config --global user.email "pei@kmglobal.com.tw"

# 5. 狀態驗證（output 會顯示在 Codex 的啟動日誌）
echo ""
echo "=== Codex Workspace Ready ==="
echo "gh:     $(gh --version 2>/dev/null | head -1 || echo 'NOT INSTALLED')"
echo "auth:   $(gh auth status 2>&1 | head -1 || echo 'NOT AUTHED')"
echo "remote: $(git remote get-url origin 2>/dev/null | sed 's|://[^@]*@|://***@|' || echo 'NO REMOTE')"
echo "user:   $(git config --get user.name) <$(git config --get user.email)>"
echo "main:   $(git rev-parse origin/main 2>/dev/null | head -c 8 || echo 'NOT FETCHED')"
echo "================================"
```

儲存。

### 2c. 如果平台不支援 Secret 或 Init Script

目前已知的替代方案（由最好到最差）：

**替代 A：Devcontainer**
若 Codex Cloud 支援 `.devcontainer/devcontainer.json` 或 `Dockerfile`，把 init script 搬進去作為 `postCreateCommand`。

**替代 B：每次 task 手動跑**
把上面的 init script 存成 `scripts/bootstrap/codex-session-init.sh` 進 repo，叫 Codex 每次 task 第一步跑：
```bash
bash scripts/bootstrap/codex-session-init.sh
```
缺點：需要手動餵 `GITHUB_TOKEN`（每個 task 在對話裡 export），token 會進對話紀錄有洩漏風險。

**替代 C：放棄自動化，維持現行流程**
Codex 改完描述給 Claude，Claude 代工 push。這是到 v4.10 的現行模式，可運作但摩擦高。

---

## Step 3：驗證

設定完之後，開一個新 Codex task 跑這段指令，Codex 回覆的輸出直接貼給 Claude 檢查：

```bash
gh --version
gh auth status
git remote -v
git config --get user.name
git config --get user.email
git rev-parse origin/main
```

### 期待輸出

```
gh version 2.x.x (...)
https://github.com/cli/cli/releases/latest

✓ Logged in to github.com account pei760730 (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token: github_pat_*****

origin  https://***@github.com/pei760730/KaiOS-ContentSystem.git (fetch)
origin  https://***@github.com/pei760730/KaiOS-ContentSystem.git (push)

pei760730

pei@kmglobal.com.tw

b516644xxxx...  # 當前 main 最新 commit
```

全對 → ✅ 配置成功
任一錯 → 貼完整錯誤給 Claude，一起 debug

---

## 驗證後給 Codex 的新工作流規範

配置成功後，Codex 從下一個 task 起遵守：

1. **每個任務開新分支**：`git checkout -b codex/<task-name> origin/main`（init script 已 fetch，base 保證最新）
2. **push 用 gh 或 git**：
   - 簡單推：`git push -u origin codex/<task-name>`
   - 推 + 開 PR：`gh pr create --base main --head codex/<task-name> --title "..." --body "..."`
3. **close PR**：`gh pr close <num> --comment "..."`
4. **刪遠端分支**：`git push origin --delete codex/<task-name>`

Claude 不再需要代工。

---

## 安全與維護

| 面向 | 做法 |
|------|------|
| Token 到期提醒 | GitHub 會在到期前 7 天寄 email |
| 懷疑 Token 洩漏 | 立刻 https://github.com/settings/tokens 按 Revoke → Step 1 重新生成 → Step 2a 更新 Secret |
| 限制 Token 範圍 | 只授權 `pei760730/KaiOS-ContentSystem` 單一 repo（Step 1 已設） |
| Audit | 定期檢查 GitHub Settings → Personal access tokens 使用紀錄 |
| 不把 Token 貼給 Claude | Claude sandbox 跟 Codex Cloud 是兩個獨立環境，Token 不應跨環境傳遞 |

---

## 未配置前的最壞情況

若 Step 2 找不到 Secret / Init Script 設定頁，Kai 有兩個選擇：

1. **走替代 B**（repo 內 script + 每次手動餵 token）
2. **直接放棄自動化**，繼續現行流程 — Codex 做完描述結果給 Kai、Kai 轉給 Claude、Claude 代工 push

這兩個選項都**不 blocking** 任何生產工作，只是摩擦較高。

---

## 檢查清單

接手此任務時照此 checklist 走：

- [ ] Step 1 GitHub 生 token（權限只限 pei760730/KaiOS-ContentSystem）
- [ ] Step 2a Codex Cloud 設 `GITHUB_TOKEN` secret
- [ ] Step 2b Codex Cloud 設 init script（整段貼上）
- [ ] Step 3 叫 Codex 跑驗證指令、確認輸出全對
- [ ] 把驗證成功的結果貼給 Claude 確認
- [ ] 更新 ROADMAP.md 的「Codex sandbox 一勞永逸配置」標 DONE

完成後，Codex 下一次交付應該是：
```
Summary
Branch: codex/xxx (base: origin/main HEAD b516644)
Commits: N commits pushed
PR: https://github.com/pei760730/KaiOS-ContentSystem/pull/XXX
Tests: 357 passed
Lint: 0 issues
```
— 完整自動化、無需 Claude 代工。
