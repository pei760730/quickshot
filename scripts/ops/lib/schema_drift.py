#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schema drift classifier (breaking/non-breaking/info)."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TABLE_ROW_RE = re.compile(r"^\|\s*`?([^`|]+?)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
HEADER_VERSION_RE = re.compile(r"^\s*>\s*version:\s*([0-9]+\.[0-9]+)", re.IGNORECASE)


def _git_show(ref, rel_path):
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{rel_path}"],
            text=True,
            encoding="utf-8",
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def _parse_required(cell):
    text = (cell or "").lower()
    if any(k in text for k in ("必填", "required", "✅", "y")):
        return "required"
    if any(k in text for k in ("選填", "optional", "null", "—", "n")):
        return "optional"
    return "unknown"


def _read_header_version(text):
    """Extract `> version: X.Y` from contract doc header (first 10 lines).

    契約文件頂部 version bump 是「意圖性協議演進」的形式宣告。
    若 old_v != new_v、底下欄位的 removed/type-changed 視為 intentional（不阻 CI）。
    """
    for line in (text or "").splitlines()[:10]:
        m = HEADER_VERSION_RE.match(line)
        if m:
            return m.group(1)
    return None


def parse_markdown_schema(text):
    fields = {}
    for line in (text or "").splitlines():
        m = TABLE_ROW_RE.match(line.strip())
        if not m:
            continue
        field = m.group(1).strip()
        if field in ("欄位", "------"):
            continue
        type_ = m.group(2).strip()
        req = _parse_required(m.group(3).strip())
        fields[field] = {"type": type_, "required": req}
    return fields


def _collect_md_drifts(base_ref="origin/main", head_ref="HEAD"):
    drifts = []
    contract_dir = ROOT / "docs" / "contracts"
    for path in sorted(contract_dir.glob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        old_text = _git_show(base_ref, rel)
        new_text = path.read_text(encoding="utf-8")
        old = parse_markdown_schema(old_text)
        new = parse_markdown_schema(new_text)
        if not old or not new:
            continue

        # v4.62+：contract 頂部 version bump = intentional evolution、breaking 降級。
        old_v = _read_header_version(old_text)
        new_v = _read_header_version(new_text)
        intentional = bool(old_v and new_v and old_v != new_v)
        breaking_level = "non-breaking" if intentional else "breaking"
        suffix = f" (intentional, v{old_v} → v{new_v})" if intentional else ""

        for f in sorted(set(old) - set(new)):
            drifts.append({"level": breaking_level, "file": rel, "field": f, "detail": f"field removed: {f}{suffix}"})
        for f in sorted(set(new) - set(old)):
            if new[f]["required"] == "required":
                drifts.append({"level": breaking_level, "file": rel, "field": f, "detail": f"field added: {f}{suffix}"})
            else:
                drifts.append({"level": "non-breaking", "file": rel, "field": f, "detail": f"field added: {f}"})
        for f in sorted(set(old) & set(new)):
            if old[f]["type"] != new[f]["type"]:
                drifts.append({"level": breaking_level, "file": rel, "field": f, "detail": f"type changed {old[f]['type']} -> {new[f]['type']}{suffix}"})
                continue
            if old[f]["required"] == "required" and new[f]["required"] == "optional":
                drifts.append({"level": "non-breaking", "file": rel, "field": f, "detail": "required -> optional"})
            elif old[f]["required"] == "optional" and new[f]["required"] == "required":
                drifts.append({"level": breaking_level, "file": rel, "field": f, "detail": f"optional -> required{suffix}"})

        if old == new:
            old_head = "\n".join((old_text or "").splitlines()[:30])
            new_head = "\n".join(new_text.splitlines()[:30])
            if old_head != new_head:
                drifts.append({"level": "info", "file": rel, "field": "-", "detail": "description/header changed"})
    return drifts


def collect_schema_drifts(base_ref="origin/main", head_ref="HEAD"):
    drifts = []
    drifts.extend(_collect_md_drifts(base_ref=base_ref, head_ref=head_ref))
    return drifts
