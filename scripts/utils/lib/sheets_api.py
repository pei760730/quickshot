#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets API helpers（含 retry）。
"""

import json
import time
import ssl
import urllib.request
import urllib.error
import urllib.parse

from .config import SHEETS_API, SPREADSHEET_ID, LOG_DATA_START_ROW


def _ctx():
    return ssl.create_default_context()


_RETRYABLE_CODES = {429, 500, 502, 503}
_MAX_RETRIES = 3


def _sheets_request(req):
    """Execute a urllib Request with retry on transient errors (429/5xx)."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, context=_ctx()) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in _RETRYABLE_CODES and attempt < _MAX_RETRIES:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"  ⏳ API {e.code}，{wait}s 後重試（{attempt+1}/{_MAX_RETRIES}）...")
                time.sleep(wait)
                # rebuild request (urlopen consumes the body)
                req = urllib.request.Request(
                    req.full_url, data=req.data, method=req.get_method(),
                    headers=dict(req.headers))
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < _MAX_RETRIES:
                wait = 2 ** attempt
                print(f"  ⏳ 網路錯誤（{e.reason}），{wait}s 後重試（{attempt+1}/{_MAX_RETRIES}）...")
                time.sleep(wait)
                req = urllib.request.Request(
                    req.full_url, data=req.data, method=req.get_method(),
                    headers=dict(req.headers))
                continue
            raise


def sheets_clear(token, sheet, range_str):
    url = f"{SHEETS_API}/{SPREADSHEET_ID}/values/{urllib.parse.quote(sheet)}!{range_str}:clear"
    req = urllib.request.Request(url, data=b"{}", method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return _sheets_request(req)


def sheets_write(token, sheet, start_cell, values):
    range_str = f"{sheet}!{start_cell}"
    url = (f"{SHEETS_API}/{SPREADSHEET_ID}/values/"
           f"{urllib.parse.quote(range_str)}?valueInputOption=USER_ENTERED")
    body = json.dumps({"range": range_str, "majorDimension": "ROWS", "values": values}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    return _sheets_request(req)


def sheets_append(token, sheet, values):
    """Append rows without overwriting existing data."""
    range_str = f"{sheet}!A1"
    url = (f"{SHEETS_API}/{SPREADSHEET_ID}/values/"
           f"{urllib.parse.quote(range_str)}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS")
    body = json.dumps({"range": range_str, "majorDimension": "ROWS", "values": values}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    return _sheets_request(req)


def sheets_read(token, sheet, range_str="A1:Z2000"):
    url = (f"{SHEETS_API}/{SPREADSHEET_ID}/values/"
           f"{urllib.parse.quote(sheet)}!{range_str}")
    req = urllib.request.Request(url,
        headers={"Authorization": f"Bearer {token}"})
    data = _sheets_request(req)
    return data.get("values", [])


def sheets_get_last_row(token, sheet, col="A"):
    """回傳指定欄位實際最後有資料的 row 號（1-indexed）；空 tab 回 0。

    用途：`_write_then_clear` 寫入後判斷 Sheets 上是否有超出新資料範圍
    的歷史殘留（例如之前同步過較多 rows、後來 rows 變少時留下的孤兒）。

    實作：`spreadsheets.values.get` 對 `col:col` range 會回傳到最後非空
    cell 所在 row（不含後續空 row）。因此 `len(values)` 即 last non-empty row。
    """
    try:
        values = sheets_read(token, sheet, range_str=f"{col}:{col}")
    except Exception:
        return 0
    return len(values)


def sheets_get_tab_names(token):
    """取得試算表所有分頁名稱清單。"""
    url = f"{SHEETS_API}/{SPREADSHEET_ID}?fields=sheets.properties.title"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    data = _sheets_request(req)
    return [s["properties"]["title"] for s in data.get("sheets", [])]


def sheets_add_tab(token, title):
    """在試算表新增一個分頁。"""
    url = f"{SHEETS_API}/{SPREADSHEET_ID}:batchUpdate"
    body = json.dumps({
        "requests": [{"addSheet": {"properties": {"title": title}}}]
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return _sheets_request(req)


def sheets_delete_tab(token, title):
    """刪除指定分頁（若不存在則靜默略過，回傳 True/False）。"""
    url = f"{SHEETS_API}/{SPREADSHEET_ID}?fields=sheets.properties"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    data = _sheets_request(req)
    sheet_id = None
    for s in data.get("sheets", []):
        if s["properties"]["title"] == title:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        return False
    url = f"{SHEETS_API}/{SPREADSHEET_ID}:batchUpdate"
    body = json.dumps({
        "requests": [{"deleteSheet": {"sheetId": sheet_id}}]
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    _sheets_request(req)
    return True


def sheets_set_validation(token, sheet_name, categories):
    """
    在指定分頁 C 欄（從第 7 列起）動態設定下拉選單。
    strict=False：不符合清單時顯示警告但不擋輸入。
    """
    url = f"{SHEETS_API}/{SPREADSHEET_ID}?fields=sheets.properties"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    meta = _sheets_request(req)
    sheet_id = None
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == sheet_name:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        return False

    url = f"{SHEETS_API}/{SPREADSHEET_ID}:batchUpdate"
    body = json.dumps({"requests": [{
        "setDataValidation": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": LOG_DATA_START_ROW - 1,
                "endRowIndex": 1000,
                "startColumnIndex": 2,
                "endColumnIndex": 3
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [{"userEnteredValue": c} for c in categories]
                },
                "showCustomUi": True,
                "strict": False
            }
        }
    }]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    _sheets_request(req)
    return True


def sheets_format_bg(token, tab_name, cells_colors):
    """設定指定儲存格的背景色。

    Args:
        token: OAuth token
        tab_name: 分頁名稱
        cells_colors: list of (row, col, r, g, b)，row/col 從 0 起算，RGB 0-1 浮點
    """
    url = f"{SHEETS_API}/{SPREADSHEET_ID}?fields=sheets.properties"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    meta = _sheets_request(req)
    sheet_id = None
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == tab_name:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        return

    requests = []
    for row, col, r, g, b in cells_colors:
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row,
                    "endRowIndex": row + 1,
                    "startColumnIndex": col,
                    "endColumnIndex": col + 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": r, "green": g, "blue": b},
                    }
                },
                "fields": "userEnteredFormat.backgroundColor",
            }
        })

    url2 = f"{SHEETS_API}/{SPREADSHEET_ID}:batchUpdate"
    body = json.dumps({"requests": requests}).encode("utf-8")
    req2 = urllib.request.Request(url2, data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    _sheets_request(req2)
