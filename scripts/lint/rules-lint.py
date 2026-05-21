#!/usr/bin/env python3
"""
Cross-file lint for the content system rules.

3-layer validation:
  Layer 1: Cross-file references (見 XXX.md, 步驟 ①②③, anchors)
  Layer 2: Canonical registry (valid states, commands, deprecated keywords)
  Layer 3: Gate (called by pre-commit hook and CI)

Usage:
  python scripts/lint/rules-lint.py          # lint all rules files
  python scripts/lint/rules-lint.py --fix    # show suggested fixes (no auto-fix)
  python scripts/lint/rules-lint.py --ci     # strict mode, non-zero exit on any error
"""

import json
import os
import re
import importlib.util
import sys
import subprocess
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / "scripts" / "lint" / "canonical-registry.json"

RULES_PATHS = [
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "CLAUDE.local.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "01-data-brain" / "template" / "CLAUDE.local.md",
    *(REPO_ROOT / ".claude" / "rules").glob("*.md"),
    *(REPO_ROOT / ".claude" / "commands").glob("*.md"),
]

# ─── Load Registry ────────────────────────────────────────────────────────────


def load_registry():
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ canonical-registry.json 找不到：{REGISTRY_PATH}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ canonical-registry.json JSON 格式錯誤：{e}")
        sys.exit(1)


# ─── Checks ───────────────────────────────────────────────────────────────────


def _file_reference_exists(ref_file, filepath):
    """Return True when a referenced file can be resolved in known repo locations."""
    basename = os.path.basename(ref_file)
    candidates = [
        REPO_ROOT / ref_file,
        filepath.parent / ref_file,
        REPO_ROOT / ".claude" / "rules" / basename,
        REPO_ROOT / "docs" / "references" / basename,
    ]
    if any(c.exists() for c in candidates):
        return True

    # Fuzzy fallback for bare filenames mentioned from prose, e.g. `brand.md`,
    # when the canonical file lives below a repo subdirectory instead of root.
    ignored_parts = {".git", "node_modules"}
    return any(
        basename == candidate.name and not ignored_parts.intersection(candidate.parts)
        for candidate in REPO_ROOT.rglob(basename)
    )


def check_file_references(content, filepath, registry, errors):
    """Check that referenced .md files exist."""
    # Match patterns like: 見 XXX.md, 載入 XXX.md, 參考 XXX.md, `XXX.md`
    patterns = [
        r"見\s+[`]?([a-zA-Z0-9_\-/]+\.md)[`]?",
        r"載入\s+[`]?([a-zA-Z0-9_\-/]+\.md)[`]?",
        r"參考\s+[`]?([a-zA-Z0-9_\-/]+\.md)[`]?",
        r"[`]([a-zA-Z0-9_\-/]+\.md)[`]",
    ]

    deprecated_files = registry.get("deprecated_files", {})
    rules_files = registry.get("rules_files", {})

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            ref_file = match.group(1)
            basename = os.path.basename(ref_file)

            # Check deprecated files
            if basename in deprecated_files:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    {
                        "file": str(filepath),
                        "line": line_num,
                        "severity": "ERROR",
                        "check": "deprecated_file",
                        "message": f"引用已廢棄檔案 '{basename}': {deprecated_files[basename]}",
                    }
                )

            # Check file exists (for rules files we know about)
            if ref_file in rules_files or basename in [
                os.path.basename(k) for k in rules_files
            ]:
                continue  # Known file, OK

            # Check if file actually exists on disk
            if not _file_reference_exists(ref_file, filepath):
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    {
                        "file": str(filepath),
                        "line": line_num,
                        "severity": "WARN",
                        "check": "missing_file",
                        "message": f"引用的檔案 '{ref_file}' 在磁碟上找不到",
                    }
                )


def check_deprecated_states(content, filepath, registry, errors):
    """Check for deprecated state keywords."""
    deprecated = registry.get("deprecated_states", {})
    # Handle nested structure: {"inspiration": {"[done]": "reason"}}
    for category, states in deprecated.items():
        if not isinstance(states, dict):
            continue
        for keyword, reason in states.items():
            for match in re.finditer(re.escape(keyword), content):
                # Skip if inside a deprecation notice or explanatory context
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                line_text = content[
                    line_start : line_end if line_end != -1 else len(content)
                ]

                # Allow mentions in deprecation notices, changelogs, or explanatory context
                skip_patterns = [
                    "廢除",
                    "已廢除",
                    "deprecated",
                    "不再有",
                    "取消",
                    "v2.0",
                    "v2.1",
                    "v2.2",
                    "移除",
                    "無需",
                ]
                if any(sp in line_text for sp in skip_patterns):
                    continue

                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    {
                        "file": str(filepath),
                        "line": line_num,
                        "severity": "ERROR",
                        "check": "deprecated_state",
                        "message": f"使用已廢棄的 {category} 狀態 '{keyword}': {reason}",
                    }
                )


def check_deprecated_commands(content, filepath, registry, errors):
    """Check for deprecated command references."""
    deprecated = registry.get("deprecated_commands", {})
    for keyword, reason in deprecated.items():
        for match in re.finditer(re.escape(keyword), content):
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.end())
            line_text = content[
                line_start : line_end if line_end != -1 else len(content)
            ]

            skip_patterns = ["廢除", "已廢除", "deprecated", "不再"]
            if any(sp in line_text for sp in skip_patterns):
                continue

            line_num = content[: match.start()].count("\n") + 1
            errors.append(
                {
                    "file": str(filepath),
                    "line": line_num,
                    "severity": "ERROR",
                    "check": "deprecated_command",
                    "message": f"引用已廢棄指令 '{keyword}': {reason}",
                }
            )


def check_cross_references(content, filepath, registry, errors):
    """Check that cross-reference anchors point to valid targets."""
    anchors = registry.get("cross_reference_anchors", {})

    # Find patterns like: 見 workflow.md 流程 A 步驟 ⑥
    # or: system-rules.md 規則 5
    ref_pattern = r"(?:見\s+)?(\w[\w\-]*\.md)\s+([\w\s步驟規則流程①-⑩A-Z0-9]+)"

    for match in re.finditer(ref_pattern, content):
        full_ref = match.group(0).strip()
        # Normalize: remove 見 prefix, collapse spaces
        normalized = re.sub(r"^見\s+", "", full_ref).strip()
        normalized = re.sub(r"\s+", " ", normalized)

        # Check against known anchors (partial match)
        found = False
        for anchor_key in anchors:
            if anchor_key in normalized or normalized in anchor_key:
                found = True
                break

        # Only flag if it looks like a specific section reference
        if not found and ("步驟" in normalized or "規則" in normalized):
            # Check if the referenced file at least exists
            ref_file = match.group(1)
            rules_files = registry.get("rules_files", {})
            basename = os.path.basename(ref_file)
            known_basenames = [os.path.basename(k) for k in rules_files]

            if basename not in known_basenames and ref_file not in rules_files:
                line_num = content[: match.start()].count("\n") + 1
                errors.append(
                    {
                        "file": str(filepath),
                        "line": line_num,
                        "severity": "WARN",
                        "check": "unknown_anchor",
                        "message": f"交叉引用 '{normalized}' 不在 canonical registry 中",
                    }
                )


def check_state_consistency(content, filepath, registry, errors):
    """Check that state keywords match the valid states dictionary."""
    valid_inspiration = registry.get("valid_states", {}).get("idea", [])

    # Check for unknown [xxx] patterns that look like states
    state_pattern = r"\[([a-z]+)\]"
    known_states = set()
    for s in valid_inspiration:
        # Support both "[inbox]" and "inbox" formats
        m = re.search(r"\[([a-z]+)\]", s)
        if m:
            known_states.add(m.group(1))
        elif re.match(r"^[a-z]+$", s):
            known_states.add(s)

    # Also add some known non-state bracket patterns to ignore
    ignore_patterns = {
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
        "x",
        "N",
        "X",
        "operator",
    }

    for match in re.finditer(state_pattern, content):
        state = match.group(1)
        if state in known_states or state in ignore_patterns:
            continue

        # Check if it's a deprecated state (nested structure)
        bracket_form = f"[{state}]"
        deprecated = registry.get("deprecated_states", {})
        is_deprecated = False
        for _cat, dep_states in deprecated.items():
            if isinstance(dep_states, dict) and bracket_form in dep_states:
                is_deprecated = True
                break
        if is_deprecated:
            # Already handled by check_deprecated_states
            continue

        # Unknown state - might be worth flagging
        line_num = content[: match.start()].count("\n") + 1
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.end())
        line_text = content[
            line_start : line_end if line_end != -1 else len(content)
        ].strip()

        # Only flag if it looks like a status marker (near 靈感/狀態 context)
        if "靈感" in line_text or "狀態" in line_text or "收集箱" in line_text:
            errors.append(
                {
                    "file": str(filepath),
                    "line": line_num,
                    "severity": "WARN",
                    "check": "unknown_state",
                    "message": f"未知狀態 '[{state}]' 不在 canonical registry 中",
                }
            )


def _read_pipeline_sharded_from_data_dir(data_dir):
    """Read operator/template sharded pipeline data without legacy pipeline.json."""
    pipeline_dir = Path(data_dir) / "pipeline"
    meta_path = pipeline_dir / "_meta.json"
    items_dir = pipeline_dir / "items"
    if not meta_path.exists() or not items_dir.exists():
        return None, meta_path
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    items = []
    for item_path in sorted(items_dir.glob("*.json")):
        try:
            item = json.loads(item_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    return {"_meta": meta, "items": items}, meta_path


def _read_pipeline_sharded_from_git(ref, operator="kai"):
    """Read sharded pipeline data from a git ref for regression comparison."""
    base = f"data/{operator}/pipeline"
    meta_proc = subprocess.run(
        ["git", "show", f"{ref}:{base}/_meta.json"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    if meta_proc.returncode != 0 or not meta_proc.stdout.strip():
        return None
    items_proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, f"{base}/items"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    try:
        meta = json.loads(meta_proc.stdout)
    except json.JSONDecodeError:
        return None
    items = []
    if items_proc.returncode == 0:
        for rel_path in items_proc.stdout.splitlines():
            if not rel_path.endswith(".json"):
                continue
            item_proc = subprocess.run(
                ["git", "show", f"{ref}:{rel_path}"],
                capture_output=True,
                text=True,
                check=False,
                cwd=REPO_ROOT,
            )
            if item_proc.returncode != 0 or not item_proc.stdout.strip():
                continue
            try:
                item = json.loads(item_proc.stdout)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                items.append(item)
    return {"_meta": meta, "items": items}


def check_tracking_json(registry, errors):
    """Validate sharded pipeline SSoT integrity for ALL operators.

    v4.38：從 ops.lib.config 動態讀 OPERATORS（原本硬寫 kai/ruby、
    ruby v4.34 EOL、且客戶 repo 的 operator 會從 data/.operators.json 動態註冊）。
    """
    # 動態 import 避免循環依賴
    import sys

    ops_lib_path = REPO_ROOT / "scripts" / "ops"
    if str(ops_lib_path) not in sys.path:
        sys.path.insert(0, str(ops_lib_path))
    from lib.config import OPERATORS as _OPERATORS  # noqa: E402

    for op_name, cfg in _OPERATORS.items():
        op_cfg = {"vid_prefix": cfg["vid_prefix"], "data_dir": cfg["data_dir"]}
        _check_single_operator_tracking(op_name, op_cfg, registry, errors)


def _check_single_operator_tracking(op_name, op_cfg, registry, errors):
    """Validate a single operator's sharded pipeline."""
    data, tracking_json = _read_pipeline_sharded_from_data_dir(op_cfg["data_dir"])
    vid_prefix = op_cfg["vid_prefix"]

    if data is None:
        errors.append(
            {
                "file": str(tracking_json),
                "line": 0,
                "severity": "WARN",
                "check": "tracking_missing",
                "message": f"[{op_name}] SSoT shard {tracking_json.name} 不存在",
            }
        )
        return

    valid_statuses = set(registry.get("valid_states", {}).get("video", []))
    # pipeline.json has both idea and video statuses
    # Add idea + terminal statuses from registry
    for category in ("idea", "terminal"):
        for s in registry.get("valid_states", {}).get(category, []):
            valid_statuses.add(s)
    seen_vids = set()
    vid_pattern = re.compile(rf"^{re.escape(vid_prefix)}-\d{{3,}}$")

    for v in data.get("items", []):
        vid = v.get("vid")
        if not vid:
            continue  # ideas without VID are valid

        # VID format（operator-aware prefix）
        if not vid_pattern.match(vid):
            errors.append(
                {
                    "file": str(tracking_json),
                    "line": 0,
                    "severity": "ERROR",
                    "check": "tracking_vid",
                    "message": f"[{op_name}] 影片碼格式錯誤：'{vid}'（應為 {vid_prefix}-NNN）",
                }
            )

        # Duplicate VID
        if vid in seen_vids:
            errors.append(
                {
                    "file": str(tracking_json),
                    "line": 0,
                    "severity": "ERROR",
                    "check": "tracking_duplicate",
                    "message": f"重複的影片碼：{vid}",
                }
            )
        seen_vids.add(vid)

        # Status validity
        status = v.get("status")
        if status not in valid_statuses:
            errors.append(
                {
                    "file": str(tracking_json),
                    "line": 0,
                    "severity": "ERROR",
                    "check": "tracking_status",
                    "message": f"'{vid}' 狀態 '{status}' 不在合法值中（{', '.join(sorted(valid_statuses))}）",
                }
            )

        # Date format
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        for field in ["publish_date"]:
            val = v.get(field)
            if val and not re.match(date_pattern, val):
                errors.append(
                    {
                        "file": str(tracking_json),
                        "line": 0,
                        "severity": "WARN",
                        "check": "tracking_date",
                        "message": f"'{vid}' {field} 格式不正確：'{val}'",
                    }
                )

        # Required fields
        for field in ["topic"]:
            if not v.get(field):
                errors.append(
                    {
                        "file": str(tracking_json),
                        "line": 0,
                        "severity": "ERROR",
                        "check": "tracking_field",
                        "message": f"'{vid}' 缺少必填欄位 {field}",
                    }
                )
        # 已上線必須有上片日
        if status == "已上線" and not v.get("publish_date"):
            errors.append(
                {
                    "file": str(tracking_json),
                    "line": 0,
                    "severity": "ERROR",
                    "check": "tracking_field",
                    "message": f"'{vid}' 已上線但缺少 publish_date",
                }
            )


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_items_by_vid(data):
    out = {}
    for item in data.get("items", []):
        vid = item.get("vid")
        if vid:
            out[vid] = item
    return out


def evaluate_pipeline_regression_guard(base_data, head_data):
    """Return list of regression messages found between base/head pipeline data."""
    issues = []

    base_meta = base_data.get("_meta", {})
    head_meta = head_data.get("_meta", {})

    base_next_vid = _parse_int(base_meta.get("next_vid"))
    head_next_vid = _parse_int(head_meta.get("next_vid"))
    if (
        base_next_vid is not None
        and head_next_vid is not None
        and head_next_vid < base_next_vid
    ):
        issues.append(
            f"❌ pipeline-regression-guard: _meta.next_vid {base_next_vid} → {head_next_vid} (regression)"
        )

    base_next_idea = _parse_int(base_meta.get("next_idea_id"))
    head_next_idea = _parse_int(head_meta.get("next_idea_id"))
    if (
        base_next_idea is not None
        and head_next_idea is not None
        and head_next_idea < base_next_idea
    ):
        issues.append(
            f"❌ pipeline-regression-guard: _meta.next_idea_id {base_next_idea} → {head_next_idea} (regression)"
        )

    base_by_vid = _build_items_by_vid(base_data)
    head_by_vid = _build_items_by_vid(head_data)

    status_regressions = []
    backfill_regressions = []

    for vid, b in base_by_vid.items():
        h = head_by_vid.get(vid)
        if not h:
            continue
        b_status = b.get("status")
        h_status = h.get("status")
        if b_status == "已上線" and h_status in {"待拍", "剪輯中"}:
            status_regressions.append((vid, b_status, h_status))

        b_backfill = b.get("backfill")
        h_backfill = h.get("backfill")
        if b_backfill is not None and h_backfill is None:
            backfill_regressions.append(vid)

    for vid, b_status, h_status in sorted(status_regressions):
        issues.append(
            f"❌ pipeline-regression-guard: {vid} status {b_status} → {h_status} (regression)"
        )
    for vid in sorted(backfill_regressions):
        issues.append(
            f"❌ pipeline-regression-guard: {vid} backfill non-null → null (regression)"
        )

    return issues


def check_pipeline_regression_guard(errors):
    """Guard against stale branch overwrite regressions on each operator's sharded pipeline."""
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    ref_name = os.getenv("GITHUB_REF_NAME", "")
    pr_body = os.getenv("PR_BODY", "")

    if "pipeline-override justified by:" in pr_body.lower():
        return

    # main push: head == base, skip compare
    if event_name == "push" and ref_name == "main":
        return

    import sys

    ops_lib_path = REPO_ROOT / "scripts" / "ops"
    if str(ops_lib_path) not in sys.path:
        sys.path.insert(0, str(ops_lib_path))
    from lib.config import OPERATORS as _OPERATORS  # noqa: E402

    for op_name in _OPERATORS:
        try:
            base_data = _read_pipeline_sharded_from_git("origin/main", operator=op_name)
        except Exception:
            continue
        if base_data is None:
            continue

        head_data, head_path = _read_pipeline_sharded_from_data_dir(
            REPO_ROOT / "data" / op_name
        )
        if head_data is None:
            continue

        for msg in evaluate_pipeline_regression_guard(base_data, head_data):
            errors.append(
                {
                    "file": str(head_path),
                    "line": 0,
                    "severity": "ERROR",
                    "check": "pipeline-regression-guard",
                    "message": msg.replace("❌ pipeline-regression-guard: ", ""),
                }
            )


def check_registry_completeness(registry, errors):
    """Check that .claude/skills/ entries and Registry valid_skills are in sync."""
    skills_dir = REPO_ROOT / ".claude" / "skills"
    stub_backfill_allowlist = {
        "orientation",
        "discovery",
        "generation",
        "quality",
        "distillation",
    }

    # Discover skills from .claude/skills/*.md
    disk_skills = set()
    if skills_dir.is_dir():
        for f in skills_dir.glob("*.md"):
            disk_skills.add(f.stem)

    # Get registry skills (support both list and dict formats)
    raw_skills = registry.get("valid_skills", [])
    if isinstance(raw_skills, dict):
        registry_skills = set()
        for tier_list in raw_skills.values():
            registry_skills.update(tier_list)
    else:
        registry_skills = set(raw_skills)

    # Skills on disk but not in Registry
    for skill in sorted(disk_skills - registry_skills):
        errors.append(
            {
                "file": str(skills_dir / f"{skill}.md"),
                "line": 0,
                "severity": "WARN",
                "check": "registry_missing_skill",
                "message": f".claude/skills/ 有 '{skill}' 但 canonical-registry.json 沒有",
            }
        )

    # Skills in Registry but not on disk
    for skill in sorted(registry_skills - disk_skills):
        if skill in stub_backfill_allowlist:
            continue
        errors.append(
            {
                "file": str(REGISTRY_PATH),
                "line": 0,
                "severity": "ERROR",
                "check": "disk_missing_skill",
                "message": f"canonical-registry.json 有 '{skill}' 但 .claude/skills/ 沒有對應 entry",
            }
        )


def _flatten_meta_keys(obj, prefix=""):
    """Flatten nested dict keys for schema comparison (list items ignored)."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            keys.add(p)
            keys |= _flatten_meta_keys(v, p)
    return keys


def check_template_schema_alignment(errors):
    """Template pipeline/_meta.json schema 應為 operator pipeline 的 superset-or-equal。

    Wave 13 反思（engine v4.89+）：template 缺了 stale_days / shelf_life_*
    / valid_verifier_predictions 等 11 欄位、新客戶 bootstrap 後 schema
    不完整。本 rule 自動偵測「任何 operator pipeline._meta 有的欄位、
    template 沒有」。

    只比 `_meta` 層 dict 欄位、忽略 list 內容（如 statuses.idea 的 list）。
    允許 template 多出 `description` 這類自描述欄位。
    """
    template, template_path = _read_pipeline_sharded_from_data_dir(
        REPO_ROOT / "data" / "template"
    )
    if template is None:
        return
    tkeys = _flatten_meta_keys(template.get("_meta", {}))

    for op_dir in (REPO_ROOT / "data").iterdir():
        if not op_dir.is_dir() or op_dir.name in {"template", ".cache"}:
            continue
        data, _ = _read_pipeline_sharded_from_data_dir(op_dir)
        if data is None:
            continue
        okeys = _flatten_meta_keys(data.get("_meta", {}))
        missing = sorted(okeys - tkeys)
        if missing:
            errors.append(
                {
                    "file": str(template_path),
                    "line": 0,
                    "severity": "WARN",
                    "check": "template_schema_drift",
                    "message": f"template._meta 缺欄位（operator={op_dir.name} 有）：{', '.join(missing[:5])}{'…' if len(missing) > 5 else ''}",
                }
            )


def check_skill_description_version_sync(errors):
    """SKILL.md description: 裡的 inline vX.YY 必須等於 version: 欄位。

    Wave 25 反思（engine v5.01+）：6 個 SKILL 描述寫 vX.Y 但 frontmatter
    version: 已 vX.YY；check-version-sync 只比 frontmatter/stub/heading/manifest
    四處、漏了 description 字串內的 inline 版本。本 rule 補這層。

    規則：description 字串裡出現 `v\\d+\\.\\d+` 時、必須等於 frontmatter `version:`。
    若 description 沒提版本（無 v\\d+\\.\\d+）→ 放過（允許簡短 description）。
    """
    skill_dir = REPO_ROOT / "02-skill-factory"
    if not skill_dir.is_dir():
        return
    for sub in skill_dir.iterdir():
        if not sub.is_dir() or sub.name in {"shared-references"}:
            continue
        skill_md = sub / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        front_m = re.search(r"^---\s*\n(.+?)\n---", text, re.DOTALL | re.MULTILINE)
        if not front_m:
            continue
        frontmatter = front_m.group(1)
        ver_m = re.search(r"^version:\s*([\d.]+)\s*$", frontmatter, re.MULTILINE)
        desc_m = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
        if not ver_m or not desc_m:
            continue
        actual = ver_m.group(1).strip()
        desc = desc_m.group(1)
        # Find all `vX.YY` / `VX.YY` in description
        inline = re.findall(r"[vV](\d+\.\d+)", desc)
        for found in inline:
            if found != actual:
                errors.append(
                    {
                        "file": str(skill_md),
                        "line": 0,
                        "severity": "ERROR",
                        "check": "skill_description_version_drift",
                        "message": f"{sub.name}: description 寫 v{found}、frontmatter version 是 {actual}",
                    }
                )


def check_skill_stub_readme_version_sync(errors):
    """Cross-check SKILL.md frontmatter version against
       (1) .claude/skills/<name>.md stub description inline vX.Y
       (2) 02-skill-factory/README.md skill table inline vX.Y

    Catches the failure mode that slipped past check_skill_description_version_sync:
    that check only validated SKILL.md description ↔ its own frontmatter version,
    leaving stub descriptions and the README table free to drift independently
    (e.g. PR #12 / #13 follow-up: generation README v1.3 vs SKILL v1.4,
    orientation stub v2.0 vs SKILL v2.1, harden stub v2.0 vs SKILL v2.1).
    """
    skill_dir = REPO_ROOT / "02-skill-factory"
    stub_dir = REPO_ROOT / ".claude" / "skills"
    readme_path = skill_dir / "README.md"
    if not skill_dir.is_dir():
        return

    skill_versions = {}
    for sub in skill_dir.iterdir():
        if not sub.is_dir() or sub.name in {"shared-references", "skill-creator"}:
            continue
        skill_md = sub / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        front_m = re.search(r"^---\s*\n(.+?)\n---", text, re.DOTALL | re.MULTILINE)
        if not front_m:
            continue
        ver_m = re.search(r"^version:\s*([\d.]+)\s*$", front_m.group(1), re.MULTILINE)
        if ver_m:
            skill_versions[sub.name] = ver_m.group(1).strip()

    # (1) Stubs
    if stub_dir.is_dir():
        for name, actual in skill_versions.items():
            stub = stub_dir / f"{name}.md"
            if not stub.exists():
                continue
            stub_text = stub.read_text(encoding="utf-8", errors="ignore")
            front_m = re.search(
                r"^---\s*\n(.+?)\n---", stub_text, re.DOTALL | re.MULTILINE
            )
            if not front_m:
                continue
            desc_m = re.search(r"^description:\s*(.+)$", front_m.group(1), re.MULTILINE)
            if not desc_m:
                continue
            for found in re.findall(r"[vV](\d+\.\d+)", desc_m.group(1)):
                if found != actual:
                    errors.append(
                        {
                            "file": str(stub),
                            "line": 0,
                            "severity": "ERROR",
                            "check": "skill_stub_version_drift",
                            "message": f"{name}: stub description 寫 v{found}、SKILL.md frontmatter version 是 {actual}",
                        }
                    )

    # (2) README table
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8", errors="ignore")
        for name, actual in skill_versions.items():
            # Match `\`<name>\`` followed (within table row) by `v<num>`
            row_re = re.compile(r"`" + re.escape(name) + r"`\s*\|\s*v(\d+\.\d+)")
            for found in row_re.findall(readme):
                if found != actual:
                    errors.append(
                        {
                            "file": str(readme_path),
                            "line": 0,
                            "severity": "ERROR",
                            "check": "skill_readme_version_drift",
                            "message": f"{name}: README 表格寫 v{found}、SKILL.md frontmatter version 是 {actual}",
                        }
                    )


def check_skill_io_contract(errors):
    """Run skill-io lint and merge findings."""
    script = REPO_ROOT / "scripts" / "lint" / "skill-io-lint.py"
    if not script.exists():
        return
    spec = importlib.util.spec_from_file_location("skill_io_lint", script)
    if not spec or not spec.loader:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_lint = getattr(module, "run_lint", None)
    if not callable(run_lint):
        return
    for issue in run_lint():
        errors.append(issue)


def check_brand_ref_contract(errors):
    """Run brand-ref lint and merge findings."""
    script = REPO_ROOT / "scripts" / "lint" / "brand_ref_lint.py"
    if not script.exists():
        return
    spec = importlib.util.spec_from_file_location("brand_ref_lint", script)
    if not spec or not spec.loader:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_lint = getattr(module, "run_lint", None)
    if not callable(run_lint):
        return
    findings, _manifest = run_lint(REPO_ROOT)
    for issue in findings:
        errors.append(issue)


def check_legacy_lesson_stage_usage(errors):
    """Warn when legacy lesson stages are used with stage filters outside migration/docs."""
    include_paths = [REPO_ROOT / "scripts" / "libs", REPO_ROOT / "02-skill-factory"]
    stage_patterns = [
        re.compile(r"stage[^\n]{0,120}\"(candidate|active|observation)\""),
        re.compile(r"\"(candidate|active|observation)\"[^\n]{0,120}stage"),
    ]

    for base in include_paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if path.suffix == ".md":
                continue
            if path.suffix != ".py":
                continue
            if rel == "scripts/ops/lib/lessons.py":
                continue
            if rel.startswith("scripts/ops/lib/migrate_"):
                continue

            for idx, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1
            ):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if any(p.search(line) for p in stage_patterns):
                    errors.append(
                        {
                            "file": str(path),
                            "line": idx,
                            "severity": "WARN",
                            "check": "legacy_lesson_stage",
                            "message": '偵測到 legacy lesson stage stage-filter（candidate/active/observation）；請改用 stage="soft"。',
                        }
                    )


# ─── Runner ───────────────────────────────────────────────────────────────────


def lint_file(filepath, registry):
    """Run all checks on a single file."""
    errors = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(
            {
                "file": str(filepath),
                "line": 0,
                "severity": "ERROR",
                "check": "read_error",
                "message": f"無法讀取檔案: {e}",
            }
        )
        return errors

    check_file_references(content, filepath, registry, errors)
    check_deprecated_states(content, filepath, registry, errors)
    check_deprecated_commands(content, filepath, registry, errors)
    check_cross_references(content, filepath, registry, errors)
    check_state_consistency(content, filepath, registry, errors)

    return errors


def main():
    ci_mode = "--ci" in sys.argv

    registry = load_registry()

    all_errors = []
    for filepath in sorted(RULES_PATHS):
        if filepath.exists():
            file_errors = lint_file(filepath, registry)
            all_errors.extend(file_errors)

    # Cross-source checks (not per-file)
    check_registry_completeness(registry, all_errors)
    check_tracking_json(registry, all_errors)
    check_template_schema_alignment(all_errors)
    check_pipeline_regression_guard(all_errors)
    check_skill_description_version_sync(all_errors)
    check_skill_stub_readme_version_sync(all_errors)
    check_skill_io_contract(all_errors)
    check_brand_ref_contract(all_errors)
    check_legacy_lesson_stage_usage(all_errors)

    # Output
    if not all_errors:
        print("✅ Rules lint passed — 0 issues found")
        sys.exit(0)

    error_count = sum(1 for e in all_errors if e["severity"] == "ERROR")
    warn_count = sum(1 for e in all_errors if e["severity"] == "WARN")

    # Group by file
    by_file = {}
    for e in all_errors:
        by_file.setdefault(e["file"], []).append(e)

    for filepath, file_errors in sorted(by_file.items()):
        rel_path = os.path.relpath(filepath, REPO_ROOT)
        print(f"\n📄 {rel_path}")
        for e in sorted(file_errors, key=lambda x: x["line"]):
            icon = "❌" if e["severity"] == "ERROR" else "⚠️"
            print(f"  {icon} L{e['line']:>3} [{e['check']}] {e['message']}")

    print(f"\n{'─' * 60}")
    print(f"結果: {error_count} errors, {warn_count} warnings")

    if ci_mode and error_count > 0:
        print("❌ CI mode: failing due to errors")
        sys.exit(1)
    elif error_count > 0:
        print("⚠️ 有 errors，建議修正後再 commit")
        sys.exit(1)
    else:
        print("✅ 只有 warnings，不阻塞 commit")
        sys.exit(0)


if __name__ == "__main__":
    main()
