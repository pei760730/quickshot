#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 雲端中繼：偵測環境 + 觸發 workflow。
"""

import json
import os
import sys
import time
import ssl
import socket
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root in sys.path so `from scripts.ops.lib.pipeline import ...` resolves
# when this module is imported from scripts/utils/sync-to-sheets.py (cwd = repo root
# but sys.path lacks it because sync-to-sheets.py is not run with `python -m`).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ops.lib.pipeline import get_pipeline_data, save_pipeline

from .config import (
    SHEETS_API, SPREADSHEET_ID, PROJECT_ROOT, TW_TZ,
    GITHUB_REPO, GITHUB_WORKFLOW, resolve_operator,
)


def _is_cloud_environment():
    """偵測是否在雲端環境（Google API 被防火牆擋住）"""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return False
    try:
        req = urllib.request.Request(
            f"{SHEETS_API}/{SPREADSHEET_ID}?fields=sheets.properties.title",
            method="GET"
        )
        ctx = ssl.create_default_context()
        urllib.request.urlopen(req, timeout=5, context=ctx)
        return False
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False
        try:
            body = e.read().decode()
            if "PERMISSION_DENIED" in body or "caller does not have permission" in body:
                return False
        except Exception:
            pass
        print(f"[cloud-detect] Sheets API HTTP {e.code}，判定為雲端環境")
        return True
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        print(f"[cloud-detect] 無法連線 Google API ({type(e).__name__}: {e})，判定為雲端環境")
        return True


def _get_github_token():
    """從環境變數或 git remote URL 取得 GitHub token"""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "github"],
            capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_ROOT
        )
        url = result.stdout.strip()
        if "@github.com" in url and "//" in url:
            return url.split("//")[1].split("@")[0]
    except Exception:
        pass
    return None


def _github_api(method, endpoint, token, data=None):
    """發送 GitHub API 請求"""
    url = f"https://api.github.com{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    if body:
        req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context()
    resp = urllib.request.urlopen(req, timeout=30, context=ctx)
    if resp.status == 204:
        return {}
    return json.loads(resp.read().decode())


def _get_current_branch():
    """取得目前 git branch 名稱"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_ROOT
        )
        return result.stdout.strip() or "main"
    except Exception:
        return "main"


def trigger_github_sync_via_push(operator=None):
    """透過 git push 觸發 GitHub Actions 同步（不需要 GitHub token）"""
    import subprocess
    ref = _get_current_branch()
    op = resolve_operator(operator)
    tracking_relpath = os.path.join("data", op, "pipeline.json")
    tracking_path = os.path.join(PROJECT_ROOT, tracking_relpath)
    tracking_shard_relpath = os.path.join("data", op, "pipeline")

    data = get_pipeline_data(pipeline_json=tracking_path)
    if data is None:
        print(f"  ❌ {tracking_shard_relpath}/_meta.json 不存在")
        return False

    print(f"\n  🔄 透過 git push 觸發 GitHub Actions 同步...")
    print(f"     分支：{ref}")

    try:
        data["sync_trigger"] = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
        # save_pipeline writes sharded data and keeps legacy pipeline.json until Phase 4.
        save_pipeline(data, skip_validate=True, pipeline_json=tracking_path)
    except Exception as e:
        print(f"  ❌ 更新 sync_trigger 失敗：{e}")
        return False

    try:
        subprocess.run(
            ["git", "add", tracking_relpath, tracking_shard_relpath],
            cwd=PROJECT_ROOT, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "sync: trigger Sheets sync via push"],
            cwd=PROJECT_ROOT, check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "push", "-u", "origin", ref],
            cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        if result.returncode != 0:
            print(f"  ❌ push 失敗：{result.stderr}")
            return False
        print("  ✅ 已 push，GitHub Actions 將自動同步")
        print("  ⏳ 通常 30-60 秒內完成，可在 Sheets 確認")
        return True
    except subprocess.TimeoutExpired:
        print("  ❌ push 逾時")
        return False
    except Exception as e:
        print(f"  ❌ git 操作失敗：{e}")
        return False


def trigger_github_sync(mode, operator=None):
    """透過 GitHub Actions 中繼同步，自動等待結果"""
    token = _get_github_token()
    if not token:
        print("  ℹ️  無 GitHub token，改用 git push 觸發 workflow...")
        return trigger_github_sync_via_push(operator=operator)

    ref = _get_current_branch()
    print("\n  🔄 透過 GitHub Actions 中繼同步...")
    print(f"     模式：{mode}　分支：{ref}")

    try:
        _github_api(
            "POST",
            f"/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches",
            token,
            {"ref": ref, "inputs": {"mode": mode, "ref": ref}}
        )
    except urllib.error.HTTPError as e:
        body = e.read().decode() if hasattr(e, "read") else str(e)
        print(f"  ❌ 觸發失敗（HTTP {e.code}）")
        if e.code == 404:
            print("  💡 workflow 不存在，請先確認 .github/workflows/sync-to-sheets.yml 已推到此分支")
        elif e.code == 422:
            print(f"  💡 可能原因：分支 {ref} 上沒有 workflow 檔案，或 Secret 未設定")
            print(f"     詳情：{body}")
        else:
            print(f"     詳情：{body}")
        return False

    print("  ✅ 已觸發 GitHub Action，等待執行...")
    dispatch_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    time.sleep(4)

    for attempt in range(24):
        try:
            runs = _github_api(
                "GET",
                f"/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/runs"
                f"?per_page=5&event=workflow_dispatch&created=%3E%3D{dispatch_time}",
                token
            )
            if runs.get("workflow_runs"):
                run = runs["workflow_runs"][0]
                status = run.get("status")
                conclusion = run.get("conclusion")

                if status == "completed":
                    if conclusion == "success":
                        print(f"  ✅ 同步成功！（耗時 ~{4 + attempt * 5}s）")
                        return True
                    else:
                        print(f"  ❌ 同步失敗（結果：{conclusion}）")
                        html_url = run.get("html_url", "")
                        if html_url:
                            print(f"  👉 查看詳情：{html_url}")
                        return False
                else:
                    elapsed = 4 + attempt * 5
                    print(f"  ⏳ {status}...（{elapsed}s）")
        except Exception as e:
            print(f"  ⚠️ 查詢狀態失敗：{e}")

        time.sleep(5)

    print("  ⏰ 等待逾時（120s），到 GitHub Actions 頁面查看：")
    print(f"  👉 https://github.com/{GITHUB_REPO}/actions")
    return False
