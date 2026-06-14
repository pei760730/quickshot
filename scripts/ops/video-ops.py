#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video-ops.py v7.0
影片 + 靈感追蹤操作腳本（pipeline.json SSoT，多操作員支援）

全域參數：
  --operator <代號>     指定操作員（預設 kai；合法值由 data/.operators.json 動態決定）

用法：
  # ── 影片操作 ──
  python scripts/ops/video-ops.py list                     # 列出所有影片
  python scripts/ops/video-ops.py get VID-004              # 查詢單支影片
  python scripts/ops/video-ops.py next-vid                 # 取得下一個可用 VID
  python scripts/ops/video-ops.py add --topic "主題" --tag "標籤" --title "標題"
  python scripts/ops/video-ops.py transition VID-004 剪輯中  # 狀態轉換
  python scripts/ops/video-ops.py delete VID-004 [--purge-script]
  python scripts/ops/video-ops.py bind-script VID-004 --script-path "03-production-line/..."
  python scripts/ops/video-ops.py list-orphans
  python scripts/ops/video-ops.py update-date VID-001 2026-01-10
  python scripts/ops/video-ops.py add-transcript VID-004 --text "逐字稿內容"
  python scripts/ops/video-ops.py validate                 # 驗證完整性
  python scripts/ops/video-ops.py validate-all             # 跨檔驗證
  # ── 靈感操作 ──
  python scripts/ops/video-ops.py add-idea --title "靈感" [--shelf-life evergreen|timely|trending]
  python scripts/ops/video-ops.py list-ideas
  python scripts/ops/video-ops.py transition-idea IDEA-001 selected
  python scripts/ops/video-ops.py confirm IDEA-001 --title "標題"
  # ── 腳本存檔 ──
  python scripts/ops/video-ops.py save VID-039 --script-path "03-production-line/02-ready-to-shoot/..." --title-type T3 --hook-type B2 --version B2 --verifier-prediction high --skill generation --mode dual-track
  # ── 快拍路線 ──
  python scripts/ops/video-ops.py quick-add --topic "主題" --tag "標籤" --title "標題"
  python scripts/ops/video-ops.py batch-quick-add
  python scripts/ops/video-ops.py query-pending-scripts
  # ── 回填操作 ──
  python scripts/ops/video-ops.py backfill VID-009 --views N --retention-3s N --completion-rate N
  python scripts/ops/video-ops.py extract-learning VID-009 --opening B2 --cta C3
  python scripts/ops/video-ops.py cleanup-formulas
  # ── lessons ──
  python scripts/ops/video-ops.py lessons add --pattern "..." --origin manual
  # ── 偏差記錄 ──
  python scripts/ops/video-ops.py record-deviation VID-009 --level minimal
  python scripts/ops/video-ops.py record-deviation VID-009 --level moderate --changes '[{"original":"原文","actual":"改後","reason":"原因"}]'
  python scripts/ops/video-ops.py diff-script VID-009 --subtitle "實際字幕全文"
  python scripts/ops/video-ops.py diff-script VID-009 --file subtitle.txt
  python scripts/ops/video-ops.py analyze-deviations
  # ── 品質記錄 ──
  python scripts/ops/video-ops.py record-verifier-scores VID-009 --conflict-score 8 --retention-prediction A --ai-residue-count 0 --data-consistency true --format-complete true --pass-count "5/5"
  # ── 選題去重 ──
  python scripts/ops/video-ops.py list-topics
  # ── 大腦健康度 ──
  python scripts/ops/video-ops.py health
  # ── 系統維護 ──
  python scripts/ops/video-ops.py migrate
  python scripts/ops/video-ops.py renumber [--dry-run]
"""

import glob
import copy
import json
import sys

# lib/ 使用 3.10+ 語法（如 `Path | None`）、系統 python3 (3.9) 會炸出難解 TypeError
if sys.version_info < (3, 10):
    sys.exit("video-ops.py 需要 Python 3.10+，請改用 repo venv 執行：.venv/bin/python scripts/ops/video-ops.py")

from datetime import datetime, timedelta
from pathlib import Path

# 確保 lib 套件可被 import（無論是 CLI 執行或被 importlib 載入）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.config import (
    PROJECT_ROOT,
    today_str,
    set_operator,
    get_operator_paths,
    DEFAULT_OPERATOR,
    VALID_OPERATORS,
)
from lib.pipeline import (
    load_tracking,
    save_tracking,
    resolve_within_repo,
    find_video,
    next_vid,
    add_video,
    transition,
    format_video,
    update_publish_date,
    renumber_videos,
    add_transcript,
    query_pending_scripts,
    load_pipeline,
    add_item as pipeline_add_item,
    transition_item as pipeline_transition_item,
    record_verifier_scores,
    validate_verifier_scores,
    save_script,
    bind_script_path,
    delete_video,
    classify_idea_freshness,
    pipeline_stats,
    set_hook_type,
)
from lib.backfill import (
    backfill_video,
    extract_learning,
    load_performance_patterns,
    save_performance_patterns,
    cleanup_unverified_formulas,
    auto_extract_from_script,
)
from lib.validate import validate, validate_all, migrate
from lib.deviations import (
    record_deviation,
    link_performance,
    analyze_deviations,
    auto_diff_and_record,
)
from lib.mistakes import record_mistake
from lib.sedimentation import get_sedimentation_context, propose_rules_from_verifier
from lib.lessons import (
    add_lesson,
    add_evidence as add_lesson_evidence,
    query as query_lessons,
    lessons_stats,
    propose_hardening as propose_lesson_hardening,
    archive_lesson,
)
from lib.todos import (
    add_todo,
    query as query_todos,
    close_todo,
    reopen_todo,
    archive_todo,
    update_todo,
)
from lib.schema_drift import collect_schema_drifts

sys.path.insert(0, str((Path(__file__).resolve().parent.parent / "utils")))
from lessons_retrieval import get_similar_vids


# ── CLI 輔助 ─────────────────────────────────────────────


def _parse_kv_args(argv, start=2):
    """將 --key value 格式的 argv 解析為 dict。"""
    result = {}
    i = start
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--") and i + 1 < len(argv):
            key = arg[2:].replace("-", "_")
            result[key] = argv[i + 1]
            i += 2
        else:
            result[f"_pos_{i}"] = arg
            i += 1
    return result


def _argv_without_flags(argv, flags):
    """Return argv with standalone boolean flags removed before --key value parsing."""
    flag_set = set(flags)
    return [arg for arg in argv if arg not in flag_set]


def _format_scalar(value):
    if value is None or value == "":
        return "N/A"
    if isinstance(value, bool):
        return "通過" if value else "未通過"
    return str(value)


def _print_save_stdout_summary(video, kv, msg):
    skill = kv.get("skill")
    mode = kv.get("mode")
    print(f"✅ {msg}")
    print(f"VID：{video.get('vid', 'N/A')}")
    print(f"主題：{_format_scalar(video.get('topic'))}")
    print(f"skill：{_format_scalar(skill)}")
    print(f"mode：{_format_scalar(mode)}")
    print(
        f"hook_type：{_format_scalar(video.get('hook_type') or kv.get('hook_type'))}"
    )
    print(f"title 候選：{_format_scalar(video.get('title'))}")
    print(
        f"品質快照：verifier_prediction={_format_scalar(video.get('verifier_prediction'))}"
    )


def _verifier_recommendation(scores):
    pass_num = int(str(scores.get("pass_count", "0/5")).split("/", 1)[0])
    blockers = []
    if scores.get("conflict_score", 0) < 7:
        blockers.append("衝突分數偏低")
    if scores.get("ai_residue_count", 0) > 0:
        blockers.append("需清 AI 殘留")
    if not scores.get("data_consistency"):
        blockers.append("需補資料一致性")
    if not scores.get("format_complete"):
        blockers.append("需補格式")
    if pass_num < 5:
        blockers.append("未滿 5/5")
    if blockers:
        return "先修正：" + "、".join(blockers)
    return "可進入拍攝；保留目前 hook 與節奏。"


def _print_verifier_stdout_summary(vid, scores, msg):
    print(f"✅ {msg}")
    print(f"VID：{vid}")
    print("體檢摘要：")
    print(f"  衝突分數：{scores['conflict_score']}/10")
    print(f"  留存預測：{scores['retention_prediction']}")
    print(f"  AI 殘留數：{scores['ai_residue_count']}")
    print(f"  資料一致性：{_format_scalar(scores['data_consistency'])}")
    print(f"  格式完整：{_format_scalar(scores['format_complete'])}")
    print(f"  5 項通過數：{scores['pass_count']}")
    print(f"建議：{_verifier_recommendation(scores)}")


def _parse_bool_arg(raw_value, key_name):
    val = (raw_value or "").strip().lower()
    if val == "true":
        return True, None
    if val == "false":
        return False, None
    return None, f"{key_name} 必須為 true 或 false"


def _rollback_save_after_verifier_failure(ctx, before_save_snapshot, reason):
    if before_save_snapshot is None:
        return
    ctx["data"].clear()
    ctx["data"].update(before_save_snapshot)
    op_paths = ctx.get("op_paths", {})
    save_tracking(ctx["data"], pipeline_json=op_paths.get("pipeline_json"))
    print(f"↩️ 已回滾 save 變更（因 {reason}）")


def _print_validate_all(data, result):
    """格式化輸出跨檔驗證報告。"""
    errs = result["errors"]
    warns = result["warnings"]

    print("🔍 跨檔驗證報告\n")

    pat_errs = [e for e in errs if e.startswith("performance-patterns")]
    vid_errs = [e for e in errs if e not in set(pat_errs)]

    v_count = len(data["videos"])

    v_icon = "✅" if not vid_errs else "❌"
    print(f"━━ pipeline.json（{v_count} 支影片）━━")
    print(f"  {v_icon} {'內部結構正常' if not vid_errs else f'{len(vid_errs)} 個問題'}")
    for e in vid_errs:
        print(f"    • {e}")

    p_icon = "✅" if not pat_errs else "❌"
    print("\n━━ performance-patterns.json ━━")
    print(
        f"  {p_icon} {'所有引用指向有效 VID' if not pat_errs else f'{len(pat_errs)} 個問題'}"
    )
    for e in pat_errs:
        print(f"    • {e}")

    cross_errs = [e for e in errs if e not in vid_errs and e not in pat_errs]
    print("\n━━ 交叉引用 + 一致性 ━━")
    if cross_errs:
        for e in cross_errs:
            print(f"  ❌ {e}")
    if warns:
        for w in warns:
            print(f"  ⚠️ {w}")
    if not cross_errs and not warns:
        print("  ✅ 所有交叉引用一致")

    total_e = len(errs)
    total_w = len(warns)
    print(f"\n🔍 結果：{total_e} 個錯誤，{total_w} 個警告")
    if total_e > 0:
        sys.exit(1)


def _cmd_list(ctx):
    for video in ctx["data"]["videos"]:
        status_icon = {"待拍": "📋", "剪輯中": "✂️", "已上線": "✅"}.get(
            video["status"], "?"
        )
        print(
            f"  {status_icon} {video['vid']} | {video['status']:4s} | {video['topic']}"
        )


def _cmd_get(ctx):
    if len(sys.argv) < 3:
        print("用法：video-ops.py get VID-NNN")
        sys.exit(1)
    _, video = find_video(ctx["data"], sys.argv[2])
    if video:
        print(format_video(video))
    else:
        print(f"找不到 {sys.argv[2]}")
        sys.exit(1)


def _cmd_next_vid(ctx):
    print(next_vid(ctx["data"], vid_prefix=ctx["op_paths"]["vid_prefix"]))


def _cmd_add(ctx):
    kv = _parse_kv_args(sys.argv)
    topic = kv.get("topic")
    tag = kv.get("tag")
    if not topic:
        print(
            '用法：video-ops.py add --topic "主題" --tag "標籤" --title "標題" --source-inspiration "靈感" [--source pipeline|quick-shot] [--initial-status 狀態] [--skill generation --mode dual-track] [--script-path 路徑] [--notes 備註] [--operator <代號>]'
        )
        sys.exit(1)
    if not tag:
        tag = "未分類"
        print("⚠️ 未提供 --tag，已使用預設標籤「未分類」")
    try:
        vid = add_video(
            ctx["data"],
            topic,
            tag,
            source_inspiration=kv.get("source_inspiration"),
            script_path=kv.get("script_path"),
            notes=kv.get("notes"),
            source=kv.get("source", "pipeline"),
            initial_status=kv.get("initial_status", "待拍"),
            script_status=kv.get("script_status"),
            skill_used=kv.get("skill"),
            title=kv.get("title"),
            vid_prefix=ctx["op_paths"]["vid_prefix"],
        )
        print(
            f"✅ 已新增 {vid}：{topic}（{tag}）[{kv.get('initial_status', '待拍')}] source={kv.get('source', 'pipeline')}"
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def _cmd_transition(ctx):
    if len(sys.argv) < 3:
        print(
            "用法：video-ops.py transition VID-NNN 新狀態 或 transition VID-NNN --to 新狀態"
        )
        sys.exit(1)
    argv = sys.argv
    vid = argv[2]
    kv = _parse_kv_args(argv, start=3)
    if kv.get("to"):
        new_status = kv.get("to")
        reason = kv.get("_pos_4") or kv.get("_pos_5")
    else:
        if len(argv) < 4:
            print(
                "用法：video-ops.py transition VID-NNN 新狀態 或 transition VID-NNN --to 新狀態"
            )
            sys.exit(1)
        new_status = argv[3]
        reason = argv[4] if len(argv) > 4 else None

    ok, msg = transition(ctx["data"], vid, new_status, reason)
    print(f"{'✅' if ok else '❌'} {msg}")
    if not ok:
        sys.exit(1)


def _cmd_delete(ctx):
    if len(sys.argv) < 3:
        print("用法：video-ops.py delete VID-NNN [--purge-script]")
        sys.exit(1)
    vid = sys.argv[2]
    purge = "--purge-script" in sys.argv[3:]

    _idx, video = find_video(ctx["data"], vid)
    if video is None:
        print(f"❌ 找不到 {vid}")
        sys.exit(1)

    sp = (video.get("script_path") or "").strip()
    removed_script = None
    if sp and sp != "系統前上線":
        abs_script = resolve_within_repo(sp)
        if abs_script is None:
            print(f"⚠️ {vid} script_path 越界 repo（{sp}），拒絕刪除檔案")
        elif abs_script.exists():
            if purge:
                abs_script.unlink()
                removed_script = sp
            elif sys.stdin.isatty():
                ans = (
                    input(f"⚠️ {vid} 連結腳本存在：{sp}，要同步刪除嗎？[y/N] ")
                    .strip()
                    .lower()
                )
                if ans in ("y", "yes"):
                    abs_script.unlink()
                    removed_script = sp

    ok, msg, _removed = delete_video(ctx["data"], vid)
    print(f"{'✅' if ok else '❌'} {msg}")
    if removed_script:
        print(f"🗑️ 已同步刪除腳本：{removed_script}")
    elif sp and not purge:
        print("ℹ️ 腳本檔未刪除（可加 --purge-script）")
    if not ok:
        sys.exit(1)


def _cmd_bind_script(ctx):
    if len(sys.argv) < 3:
        print('用法：video-ops.py bind-script VID-NNN --script-path "路徑" [--force]')
        sys.exit(1)
    vid = sys.argv[2]
    kv = _parse_kv_args(sys.argv, start=3)
    sp = kv.get("script_path")
    if not sp:
        print("❌ 缺少 --script-path 參數")
        sys.exit(1)
    force = "--force" in sys.argv[3:]
    ok, msg = bind_script_path(ctx["data"], vid, sp, force=force)
    print(f"{'✅' if ok else '❌'} {msg}")
    if not ok:
        sys.exit(1)


def _cmd_list_orphans(ctx):
    videos = ctx["data"].get("videos", [])
    tracked_paths = set()
    missing_binding = []
    for v in videos:
        sp = (v.get("script_path") or "").strip()
        if sp:
            tracked_paths.add(sp)
        else:
            missing_binding.append(v)

    prod_subdir = ctx["op_paths"]["production_subdir"]
    root = PROJECT_ROOT
    disk_paths = []
    patterns = [
        root / "03-production-line" / "02-ready-to-shoot" / prod_subdir / "*.md",
        root / "03-production-line" / "03-done" / prod_subdir / "*.md",
    ]
    for pattern in patterns:
        disk_paths.extend(Path(p) for p in sorted(glob.glob(str(pattern))))

    disk_orphans = []
    for p in disk_paths:
        rel = p.relative_to(root).as_posix()
        if rel not in tracked_paths:
            disk_orphans.append(rel)

    print(f"📎 pipeline 缺 script_path 的影片：{len(missing_binding)}")
    for v in missing_binding[:50]:
        print(f"  • {v.get('vid')} | {v.get('status')} | {v.get('topic')}")
    print(f"🗂️ 磁碟孤兒腳本：{len(disk_orphans)}")
    for sp in disk_orphans[:100]:
        print(f"  • {sp}")


def _cmd_update_date(ctx):
    if len(sys.argv) < 4:
        print("用法：video-ops.py update-date VID-NNN YYYY-MM-DD")
        print("  更新上片日，同時自動重命名腳本檔案")
        sys.exit(1)
    vid = sys.argv[2]
    new_date = sys.argv[3]
    ok, msg, old_path, new_path = update_publish_date(ctx["data"], vid, new_date)
    print(f"{'✅' if ok else '❌'} {msg}")
    if ok and old_path:
        print(f"  📂 {old_path}")
        print(f"  → {new_path}")
    if not ok:
        sys.exit(1)


def _cmd_set_hook_type(ctx):
    kv = _parse_kv_args(sys.argv)
    if len(sys.argv) < 3 or not sys.argv[2].startswith("VID-"):
        print(
            "用法：video-ops.py set-hook-type VID-NNN --hook-type B1|B2|B3|D1|D2|D3|D4|D5"
        )
        print("  回填既有影片的 hook_type（quick-shot 存量補齊用）")
        sys.exit(1)
    vid = sys.argv[2]
    hook_type = kv.get("hook_type")
    if not hook_type:
        print("❌ 缺少 --hook-type（合法值：B1/B2/B3/D1/D2/D3/D4/D5）")
        sys.exit(1)
    ok, msg = set_hook_type(ctx["data"], vid, hook_type)
    print(f"{'✅' if ok else '❌'} {msg}")
    if not ok:
        sys.exit(1)


def _cmd_add_transcript(ctx):
    if len(sys.argv) < 4:
        print(
            '用法：video-ops.py add-transcript VID-NNN --text "逐字稿" 或 --file path.txt'
        )
        sys.exit(1)
    vid = sys.argv[2]
    kv = _parse_kv_args(sys.argv, start=3)
    text = kv.get("text")
    file_path = kv.get("file")
    if file_path:
        p = Path(file_path)
        if not p.exists():
            print(f"❌ 檔案不存在：{file_path}")
            sys.exit(1)
        if p.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
            print(f"❌ 檔案過大（{p.stat().st_size // 1024 // 1024}MB），上限 10MB")
            sys.exit(1)
        text = p.read_text(encoding="utf-8")
    if not text:
        print("❌ 請提供 --text 或 --file 參數")
        sys.exit(1)
    ok, msg = add_transcript(ctx["data"], vid, text)
    print(f"{'✅' if ok else '❌'} {msg}")
    if not ok:
        sys.exit(1)


def _cmd_quick_add(ctx):
    kv = _parse_kv_args(sys.argv)
    topic = kv.get("topic")
    tag = kv.get("tag")
    title = kv.get("title")
    if not topic or not tag or not title:
        print(
            '用法：video-ops.py quick-add --topic "主題" --tag "標籤" --title "標題" [--status 待拍|剪輯中|已上線] [--initial-status 待拍|剪輯中|已上線] [--hook-type B1|B2|B3|D1|D2|D3|D4|D5] [--notes 備註]'
        )
        sys.exit(1)
    initial_status = kv.get("initial_status") or kv.get("status", "剪輯中")
    allowed_statuses = set(
        ctx["data"].get("_meta", {}).get("statuses", {}).get("video")
        or ["待拍", "剪輯中", "已上線"]
    )
    if initial_status not in allowed_statuses:
        print(
            f"❌ quick-add 只允許 --status/--initial-status {', '.join(sorted(allowed_statuses))}（收到：{initial_status}）"
        )
        sys.exit(1)

    hook_type = kv.get("hook_type")
    try:
        vid = add_video(
            ctx["data"],
            topic,
            tag,
            source_inspiration=kv.get("source_inspiration", topic),
            title=title,
            source="quick-shot",
            initial_status=initial_status,
            script_status="待補",
            notes=kv.get("notes"),
            vid_prefix=ctx["op_paths"].get("vid_prefix", "VID"),
            hook_type=hook_type,
        )
        status_icon = {"待拍": "🎬", "剪輯中": "✂️", "已上線": "✅"}.get(
            initial_status, "🎬"
        )
        hook_suffix = f" hook={hook_type}" if hook_type else ""
        print(
            f"✅ 快拍補登 {vid}：{topic}（{tag}）{status_icon} [{initial_status}]{hook_suffix}"
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def _cmd_batch_quick_add(ctx):
    import json as _json

    raw = None
    kv = _parse_kv_args(sys.argv)
    file_path = kv.get("file")
    if file_path:
        p = Path(file_path)
        if not p.exists():
            print(f"❌ 檔案不存在：{file_path}")
            sys.exit(1)
        raw = p.read_text(encoding="utf-8")
    else:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
        else:
            print("用法：video-ops.py batch-quick-add --file items.json")
            print(
                '  或：echo \'[{"topic":"X","tag":"Y","title":"Z"}]\' | video-ops.py batch-quick-add'
            )
            print(
                'JSON 格式：[{"topic": "主題", "tag": "標籤", "title": "標題", "status": "剪輯中", "hook_type": "B2"}]'
            )
            sys.exit(1)
    try:
        items = _json.loads(raw)
    except _json.JSONDecodeError as e:
        print(f"❌ JSON 解析失敗：{e}")
        sys.exit(1)
    if not isinstance(items, list):
        print("❌ JSON 根節點必須是陣列")
        sys.exit(1)

    created = []
    buffered = []
    for i, it in enumerate(items, start=1):
        topic = it.get("topic")
        tag = it.get("tag")
        title = it.get("title")
        status = it.get("status", "剪輯中")
        hook_type = it.get("hook_type")
        if not topic or not tag or not title:
            print(f"❌ 第 {i} 筆缺少 topic/tag/title")
            sys.exit(1)
        if status not in ("剪輯中", "已上線"):
            print(f"❌ 第 {i} 筆 status 只能是 剪輯中 或 已上線（收到：{status}）")
            sys.exit(1)
        try:
            vid = add_video(
                ctx["data"],
                topic,
                tag,
                source_inspiration=it.get("source_inspiration", topic),
                title=title,
                source="quick-shot",
                initial_status=status,
                script_status="待補",
                notes=it.get("notes"),
                vid_prefix=ctx["op_paths"]["vid_prefix"],
                persist=False,
                hook_type=hook_type,
            )
            buffered.append((vid, topic, tag, status))
        except ValueError as e:
            print(f"❌ 第 {i} 筆新增失敗：{e}")
            sys.exit(1)

    # 全部驗證通過後一次落盤
    save_tracking(ctx["data"])
    created.extend(buffered)

    print(f"✅ 批次新增完成：{len(created)} 筆")
    for vid, topic, tag, status in created:
        icon = "✂️" if status == "剪輯中" else "✅"
        print(f"  - {vid}：{topic}（{tag}）{icon} [{status}]")


def _cmd_query_pending_scripts(ctx):
    pending = query_pending_scripts(ctx["data"])
    if not pending:
        print("🎉 所有影片腳本都已補齊")
    else:
        print(f"📝 腳本待補（{len(pending)} 支）：")
        for item in pending:
            days = item["days_pending"]
            icon = "🔴" if days >= 14 else "🟡" if days >= 7 else "📝"
            transcript = " 📄有逐字稿" if item["has_transcript"] else ""
            print(
                f"  {icon} {item['vid']} | {item['topic']} | {item['status']} | 待補 {days} 天{transcript}"
            )


def _cmd_add_idea(_ctx):
    kv = _parse_kv_args(sys.argv)
    title = kv.get("title")
    if not title:
        print(
            '用法：video-ops.py add-idea --title "靈感" [--tags "#標籤"] [--shelf-life evergreen|timely|trending]'
        )
        sys.exit(1)
    pdata = load_pipeline()
    shelf_life = kv.get("shelf_life")
    try:
        idea_id = pipeline_add_item(
            pdata, title, tags=kv.get("tags", ""), shelf_life=shelf_life
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    sl_note = f" [{shelf_life}]" if shelf_life else ""
    print(f"✅ 已新增 {idea_id}：{title}{sl_note}")


def _cmd_list_ideas(_ctx):
    pdata = load_pipeline()
    thresholds = pdata.get("_meta", {}).get("thresholds", {})
    status_icons = {
        "inbox": "📥",
        "selected": "⭐",
        "cooldown": "❄️",
        "待拍": "📋",
        "剪輯中": "✂️",
        "已上線": "✅",
        "archived": "🗄️",
    }
    idea_statuses = {"inbox", "selected", "cooldown"}
    ideas = [i for i in pdata["items"] if i["status"] in idea_statuses]
    decorated = []
    for item in ideas:
        label, sort_key = classify_idea_freshness(item, thresholds)
        decorated.append((sort_key, item.get("created_date", ""), label, item))
    decorated.sort(key=lambda t: (t[0], t[1]))
    freshness_tag = {
        "expired": " ⚠️ 過期",
        "stale": " ⏰ 快過期",
    }
    for _sk, _cd, label, item in decorated:
        icon = status_icons.get(item["status"], "?")
        vid_note = f" → {item['vid']}" if item.get("vid") else ""
        sl_note = f" [{item['shelf_life']}]" if item.get("shelf_life") else ""
        tag = freshness_tag.get(label, "")
        print(
            f"  {icon} {item['idea_id']} | {item['status']:9s} | {item['topic']}{vid_note}{sl_note}{tag}"
        )


def _cmd_transition_idea(_ctx):
    if len(sys.argv) < 4:
        print("用法：video-ops.py transition-idea IDEA-NNN 新狀態")
        sys.exit(1)
    pdata = load_pipeline()
    ok, msg, _ = pipeline_transition_item(pdata, sys.argv[2], sys.argv[3])
    print(f"{'✅' if ok else '❌'} {msg}")
    if not ok:
        sys.exit(1)


def _cmd_confirm(_ctx):
    if len(sys.argv) < 3:
        print(
            '用法：video-ops.py confirm IDEA-NNN [--title "封面標題"] [--skill generation --mode dual-track]'
        )
        sys.exit(1)
    idea_id = sys.argv[2]
    kv = _parse_kv_args(sys.argv, start=3)
    pdata = load_pipeline()
    ok, msg, _vid_assigned = pipeline_transition_item(
        pdata,
        idea_id,
        "待拍",
        title=kv.get("title"),
        skill_used=kv.get("skill"),
        source_inspiration=kv.get("source_inspiration"),
    )
    if ok:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)


def _cmd_save(ctx):
    quiet = "--quiet" in sys.argv
    argv = _argv_without_flags(sys.argv, ["--quiet"])
    if len(argv) < 3:
        print(
            "用法：video-ops.py save VID-NNN --script-path PATH --title-type T1 --hook-type B2 --version B2 --verifier-prediction high [--quiet]"
        )
        sys.exit(1)
    vid = argv[2]
    kv = _parse_kv_args(argv, start=3)
    required = {
        "script_path": "--script-path",
        "title_type": "--title-type",
        "hook_type": "--hook-type",
        "version": "--version",
        "verifier_prediction": "--verifier-prediction",
    }
    missing = [flag for key, flag in required.items() if not kv.get(key)]
    if missing:
        print(f"❌ 缺少必填參數：{', '.join(missing)}")
        sys.exit(1)
    _, current_video = find_video(ctx["data"], vid)
    if current_video is None:
        print(f"❌ 找不到 {vid}")
        sys.exit(1)
    verifier_scores = None
    before_save_snapshot = None
    raw_verifier_scores = kv.get("verifier_scores")
    if raw_verifier_scores:
        try:
            parsed_scores = json.loads(raw_verifier_scores)
        except json.JSONDecodeError as e:
            print(f"❌ --verifier-scores 不是合法 JSON：{e}")
            sys.exit(1)
        if not isinstance(parsed_scores, dict):
            print("❌ --verifier-scores 必須是 JSON object（例如 conflict_score=8）")
            sys.exit(1)
        verifier_scores = parsed_scores
        ok_vs_validate, normalized_or_msg = validate_verifier_scores(verifier_scores)
        if not ok_vs_validate:
            print(f"❌ --verifier-scores 驗證失敗：{normalized_or_msg}")
            sys.exit(1)
        verifier_scores = normalized_or_msg
        before_save_snapshot = copy.deepcopy(ctx["data"])

    ok, msg = save_script(
        ctx["data"],
        vid,
        script_path=kv["script_path"],
        title_type=kv["title_type"],
        hook_type=kv["hook_type"],
        version=kv["version"],
        verifier_prediction=kv["verifier_prediction"],
        skill_used=kv.get("skill"),
    )
    if not ok:
        print(f"❌ {msg}")
        sys.exit(1)
    if verifier_scores is not None:
        try:
            ok_vs, msg_vs = record_verifier_scores(ctx["data"], vid, verifier_scores)
            if not ok_vs:
                print(f"❌ {msg_vs}")
                _rollback_save_after_verifier_failure(
                    ctx, before_save_snapshot, "verifier_scores 寫入失敗"
                )
                print(
                    "⚠️ save 已完成，但 verifier_scores 未成功寫入，請修正後重試 record-verifier-scores"
                )
                sys.exit(1)
            if not quiet:
                _, saved_video = find_video(ctx["data"], vid)
                _print_save_stdout_summary(saved_video or {"vid": vid}, kv, msg)
                _print_verifier_stdout_summary(vid, verifier_scores, msg_vs)
        except Exception as e:
            _rollback_save_after_verifier_failure(
                ctx, before_save_snapshot, "verifier_scores 寫入例外"
            )
            print(f"❌ verifier_scores 寫入發生例外：{e}")
            sys.exit(1)
        return
    _, saved_video = find_video(ctx["data"], vid)
    if not quiet:
        _print_save_stdout_summary(saved_video or {"vid": vid}, kv, msg)
        if saved_video is not None and not saved_video.get("verifier_scores"):
            print(
                "提醒：尚未記錄 verifier_scores；請執行 record-verifier-scores 完成體檢摘要。"
            )


def _load_json_object_from_stdin(flag_name):
    raw = sys.stdin.read()
    if not raw.strip():
        print(f"❌ {flag_name} 啟用時 stdin 不可為空")
        sys.exit(1)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"❌ stdin JSON 解析失敗：{e}")
        sys.exit(1)
    if not isinstance(payload, dict):
        print("❌ stdin JSON 必須是 JSON object")
        sys.exit(1)
    return payload


def _load_vid_inference_entries(log_path: Path):
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _cmd_vid_inference_stats():
    log_path = PROJECT_ROOT / "data/.adoption-stats/vid_inference.jsonl"
    rows = _load_vid_inference_entries(log_path)
    today = datetime.utcnow().date()

    def _window(days):
        since = today - timedelta(days=days - 1)
        scoped = []
        for r in rows:
            ts = (r.get("ts") or "").strip()
            if not ts:
                continue
            try:
                d = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
            except Exception:
                continue
            if d >= since:
                scoped.append(r)
        fenced = sum(1 for r in scoped if r.get("had_fenced"))
        inferred = sum(
            1 for r in scoped if r.get("had_fenced") and r.get("vid_inferred")
        )
        miss_rate = 0.0 if fenced == 0 else ((fenced - inferred) / fenced) * 100.0
        return fenced, inferred, miss_rate

    for days in (7, 30):
        fenced, inferred, miss_rate = _window(days)
        print(
            f"last {days}d:  fenced_blocks={fenced}, vid_inferred={inferred}, miss_rate={miss_rate:.1f}%"
        )

    _fenced30, _inferred30, miss30 = _window(30)
    if miss30 > 10.0:
        print("alert: ⚠️ miss_rate > 10% (last 30d) — consider making VID required")


def _cmd_adoption_stats(ctx):
    kv = _parse_kv_args(sys.argv, start=2)
    if "vid_inference" in kv:
        _cmd_vid_inference_stats()
        return
    try:
        recent_n = int(kv.get("n", 30))
    except (ValueError, TypeError):
        print("❌ --n 需為整數")
        sys.exit(1)
    videos = [v for v in ctx["data"].get("videos", []) if v.get("status") == "已上線"]
    videos.sort(key=lambda v: v.get("publish_date") or "", reverse=True)
    subset = videos[:recent_n]

    def _coverage(rows, key):
        if not rows:
            return 0.0, 0, 0
        hit = sum(1 for r in rows if r.get(key))
        return (hit / len(rows)) * 100.0, hit, len(rows)

    print(f"📊 adoption-stats（已上線近 {recent_n} 支）")
    for label, key in [
        ("hook_type", "hook_type"),
        ("verifier_scores", "verifier_scores"),
    ]:
        pct, hit, total = _coverage(subset, key)
        print(f"- {label}: {hit}/{total} ({pct:.1f}%)")

    today = datetime.utcnow().date()
    for days in (7, 30):
        since = today - timedelta(days=days - 1)
        window = []
        for v in videos:
            pd = v.get("publish_date")
            try:
                d = datetime.strptime(pd, "%Y-%m-%d").date()
            except Exception:
                continue
            if d >= since:
                window.append(v)
        print(f"\n📈 {days} 日趨勢（{since} ~ {today}）")
        for label, key in [
            ("hook_type", "hook_type"),
            ("verifier_scores", "verifier_scores"),
        ]:
            pct, hit, total = _coverage(window, key)
            print(f"- {label}: {hit}/{total} ({pct:.1f}%)")


def _cmd_convert_idea(_ctx):
    if len(sys.argv) < 4:
        print(
            '⚠️ convert-idea 已廢除，請改用：video-ops.py confirm IDEA-NNN --title "標題"'
        )
        sys.exit(1)
    idea_id = sys.argv[2]
    pdata = load_pipeline()
    ok, msg, _vid_assigned = pipeline_transition_item(pdata, idea_id, "待拍")
    if ok:
        print(f"✅ {msg}")
        print(f"⚠️ convert-idea 已廢除，下次請用：video-ops.py confirm {idea_id}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)


def _cmd_backfill(ctx):
    if len(sys.argv) < 4:
        print(
            "用法：video-ops.py backfill VID-NNN --views N --retention-3s N --completion-rate N [--engagement-rate N] [--profile-clicks N] [--likes N] [--comments N] [--shares N] [--saves N]"
        )
        sys.exit(1)
    vid = sys.argv[2]
    kwargs = {}
    arg_map = {
        "--views": ("views", int),
        "--retention-3s": ("retention_3s", float),
        "--completion-rate": ("completion_rate", float),
        "--engagement-rate": ("engagement_rate", float),
        "--profile-clicks": ("profile_clicks", int),
        "--likes": ("likes", int),
        "--comments": ("comments", int),
        "--shares": ("shares", int),
        "--saves": ("saves", int),
        "--reposts": ("reposts", int),
        "--new-followers": ("new_followers", int),
        "--reached-accounts": ("reached_accounts", int),
        "--video-length": ("video_length_seconds", int),
        "--avg-watch-seconds": ("avg_watch_seconds", float),
        "--profile-source-pct": ("profile_source_pct", float),
    }
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in arg_map and i + 1 < len(sys.argv):
            key, typ = arg_map[arg]
            try:
                kwargs[key] = typ(sys.argv[i + 1])
            except (ValueError, TypeError, OverflowError):
                print(f"❌ {arg} 值無效：{sys.argv[i + 1]}（應為 {typ.__name__}）")
                sys.exit(1)
            i += 2
        else:
            print(f"❌ 未知參數：{arg}")
            sys.exit(1)

    required = ["views", "retention_3s", "completion_rate"]
    missing = [k for k in required if k not in kwargs]
    if missing:
        print(
            f"❌ 缺少必填參數：{', '.join('--' + k.replace('_', '-') for k in missing)}"
        )
        sys.exit(1)

    ok, msg, result = backfill_video(ctx["data"], vid, **kwargs)
    if ok:
        icons = {"high": "🏆", "normal": "⚠️", "low": "📉"}
        r = result
        for w in r.get("warnings", []):
            print(f"  ⚠️ {w}")
        print(f"✅ {vid} 回填完成")
        print(
            f"📊 觀看 {r['views']:,} | 3秒留存 {r['retention_3s']}% | 完播 {r['completion_rate']}%"
        )
        path_note = f"路徑 {r['path']}" if r["path"] else ""
        print(
            f"{icons.get(r['level'], '?')} 判定：{r['level']}（{r['reason']}）{path_note}"
        )
        al = r.get("auto_learning")
        if al:
            action = al["action"]
            if action == "auto_high":
                print(
                    f"🎓 自動提取（高表現）：opening={al.get('opening', '—')} cta={al.get('cta', '—')}"
                )
            elif action == "auto_low":
                print(f"🎓 自動提取（低表現）：{al['failure_mode']}")
            elif action == "skip_normal":
                pass
            elif action in ("need_manual_high", "need_manual_low"):
                print(f"⚠️ {al['msg']}")
        elif r["level"] == "high":
            print(
                f'→ 建議執行：video-ops.py extract-learning {vid} --opening CODE --cta CODE --formula "..."'
            )
        elif r["level"] == "low":
            print(
                f'→ 建議執行：video-ops.py extract-learning {vid} --failure-mode "原因"'
            )
        g3 = r.get("lite_g3")
        if g3:
            if g3["pass"]:
                print(f"📱 輕量 G3 分析：✅ 通過（{', '.join(g3['checked_items'])}）")
            else:
                print(f"📱 輕量 G3 分析：⚠️ {len(g3['issues'])} 個注意項")
                for issue in g3["issues"]:
                    print(f"  • {issue}")
        diag = r.get("diagnosis")
        if diag:
            print("🔍 診斷：")
            pt = diag.get("post_type")
            if pt:
                print(f"  類型：{pt}（{diag.get('post_type_detail', '')}）")
            elif diag.get("missing_fields"):
                missing = ", ".join(diag["missing_fields"])
                print(f"  類型：未分類（缺 {missing}）")
            for s in diag.get("strengths", []):
                print(f"  💪 {s}")
            for w in diag.get("weaknesses", []):
                print(f"  ⚠️ {w}")
            for p in diag.get("prescriptions", []):
                print(f"  💊 {p}")
        context = get_sedimentation_context(
            ctx["data"].get("items", ctx["data"].get("videos", [])),
            vid=vid,
            operator=ctx["op_paths"]["label"].lower(),
            meta=ctx["data"].get("_meta"),
        )
        proposals = propose_rules_from_verifier(
            ctx["data"].get("items", ctx["data"].get("videos", [])),
            meta=ctx["data"].get("_meta"),
            operator=ctx["op_paths"]["operator"],
        )
        max_proposals = (
            context.get("limits", {}).get("max_proposals", 2)
            if isinstance(context, dict)
            else 2
        )
        pending = [p for p in proposals if not p.get("already_exists")][:max_proposals]
        cache_dir = PROJECT_ROOT / "data" / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "last-backfill-context.json"
        cache_path.write_text(
            json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"🧠 sedimentation context 已準備（cache: {cache_path.relative_to(PROJECT_ROOT)}）"
        )
        # 雙路徑交棒：cache 保留機讀；stdout 提供 Claude 當前對話可直接吸收
        print(
            f"🧠 sedimentation_context_json={json.dumps(context, ensure_ascii=False)}"
        )
        if pending:
            print(f"🧪 sedimentation proposals（待確認 {len(pending)} 條）：")
            for p in pending:
                pr = p.get("proposed_rule") or {}
                print(f"  • {p.get('issue_type')}: {pr.get('pattern', '')}")
        else:
            print("🧪 sedimentation proposals：目前無新增提案")
    else:
        print(f"❌ {msg}")
        sys.exit(1)


def _cmd_extract_learning(ctx):
    if len(sys.argv) < 4:
        print(
            '用法：video-ops.py extract-learning VID-NNN --opening CODE --cta CODE [--hook "..."] [--formula "..."]'
        )
        print(
            '  低表現：video-ops.py extract-learning VID-NNN --failure-mode "原因" [--failure-detail "..."]'
        )
        sys.exit(1)
    vid = sys.argv[2]
    kwargs = {}
    str_args = {
        "--opening": "opening",
        "--hook": "hook",
        "--turning-point": "turning_point",
        "--cta": "cta",
        "--formula": "formula",
        "--failure-mode": "failure_mode",
        "--failure-detail": "failure_detail",
    }
    skip_flag = False
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--skip":
            skip_flag = True
            i += 1
        elif arg in str_args and i + 1 < len(sys.argv):
            kwargs[str_args[arg]] = sys.argv[i + 1]
            i += 2
        else:
            print(f"❌ 未知參數：{arg}")
            sys.exit(1)

    if skip_flag:
        idx_v, video_v = find_video(ctx["data"], vid)
        if video_v and video_v.get("backfill"):
            video_v["backfill"]["learning_extracted"] = True
            video_v["learning"] = {"extracted_date": today_str(), "type": "skipped"}
            ctx["data"]["videos"][idx_v] = video_v
            save_tracking(ctx["data"])
            print(f"✅ {vid} 學習提取已跳過（標記完成）")
        else:
            print(f"❌ {vid} 無法跳過（找不到或尚未回填）")
            sys.exit(1)
    else:
        ok, msg = extract_learning(ctx["data"], vid, **kwargs)
        print(f"{'✅' if ok else '❌'} {msg}")
        if not ok:
            sys.exit(1)


def _cmd_cleanup_formulas(_ctx):
    pdata = load_performance_patterns()
    moved = cleanup_unverified_formulas(pdata)
    if not moved:
        print("✅ 所有 proven_formulas 都有 VID 證據，無需清理")
    else:
        save_performance_patterns(pdata)
        print(f"🧹 已移動 {len(moved)} 個零證據公式到 unverified_formulas：")
        for item in moved:
            print(f"  • {item['formula'][:40]}...")


def _cmd_record_deviation(ctx):
    if len(sys.argv) < 4:
        print(
            "用法：video-ops.py record-deviation VID-NNN --level minimal|moderate|significant [--changes '[{...}]']"
        )
        sys.exit(1)
    vid = sys.argv[2]
    kv = _parse_kv_args(sys.argv, start=3)
    level = kv.get("level")
    if not level:
        print("❌ 缺少 --level 參數（minimal / moderate / significant）")
        sys.exit(1)
    changes = None
    raw_changes = kv.get("changes")
    if raw_changes:
        import json as _json

        try:
            changes = _json.loads(raw_changes)
        except _json.JSONDecodeError as e:
            print(f"❌ --changes JSON 解析失敗：{e}")
            sys.exit(1)
    ok, msg = record_deviation(vid, level, changes=changes)
    if ok:
        print(f"✅ {msg}")
        idx, video = find_video(ctx["data"], vid)
        if video:
            bf = video.get("backfill") or {}
            perf = bf.get("performance")
            if perf:
                link_performance(vid, perf)
                print(f"  📊 已連結表現等級：{perf}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)


def _cmd_diff_script(_ctx):
    if len(sys.argv) < 4:
        print(
            "用法：video-ops.py diff-script VID-NNN --subtitle '字幕全文' 或 --file subtitle.txt"
        )
        sys.exit(1)
    vid = sys.argv[2]
    kv = _parse_kv_args(sys.argv, start=3)
    subtitle_text = kv.get("subtitle")
    subtitle_file = kv.get("file")
    if subtitle_file:
        p = Path(subtitle_file)
        if not p.exists():
            print(f"❌ 檔案不存在：{subtitle_file}")
            sys.exit(1)
        subtitle_text = p.read_text(encoding="utf-8")
    if not subtitle_text:
        print("❌ 請提供 --subtitle '字幕文字' 或 --file 字幕檔案路徑")
        sys.exit(1)
    ok, result = auto_diff_and_record(vid, subtitle_text)
    if ok:
        print(f"✅ {vid} 偏差自動比對完成")
        print(f"📊 {result['summary']}")
        print(
            f"   等級：{result['level']}（相似度 {round(result['similarity'] * 100)}%）"
        )
        changes = result["changes"]
        if changes:
            print(f"\n🔍 具體改動（{len(changes)} 處）：")
            for i, c in enumerate(changes[:15], 1):
                t = c["type"]
                if t == "modified":
                    print(f"  {i}. 改詞：「{c['original']}」→「{c['actual']}」")
                elif t == "removed":
                    print(f"  {i}. 刪除：「{c['original']}」")
                elif t == "added":
                    print(f"  {i}. 新增：「{c['actual']}」")
            if len(changes) > 15:
                print(f"  ...還有 {len(changes) - 15} 處")
        if result.get("performance_linked"):
            print(f"  📊 已連結表現等級：{result['performance_linked']}")
    else:
        print(f"❌ {result}")
        sys.exit(1)


def _cmd_analyze_deviations(_ctx):
    report = analyze_deviations()
    if report["total"] == 0:
        print("📊 尚無偏差記錄。回填後使用 record-deviation 開始收集。")
    elif not report["sufficient"]:
        print(f"📊 已收集 {report['total']} 筆偏差記錄（需 ≥ 10 筆才觸發完整分析）")
        print(f"  有改動：{report['with_changes']} 筆")
        dist = report["level_dist"]
        print(
            f"  等級分佈：minimal={dist['minimal']} moderate={dist['moderate']} significant={dist['significant']}"
        )
    else:
        print(f"📊 偏差分析（基於 {report['total']} 支影片）\n")
        dist = report["level_dist"]
        print(
            f"等級分佈：minimal={dist['minimal']} moderate={dist['moderate']} significant={dist['significant']}"
        )
        print(f"有改動記錄：{report['with_changes']} 筆\n")
        print("等級 × 表現交叉：")
        for lv in ("minimal", "moderate", "significant"):
            p = report["perf_by_level"][lv]
            print(f"  {lv:12s} → high={p['high']} normal={p['normal']} low={p['low']}")
        originals = report.get("frequent_originals", [])
        if originals:
            print("\n🔴 常被改的句型（建議加入 banned-words）：")
            for item in originals[:10]:
                perfs = item["performances"]
                high_pct = round(perfs.count("high") / len(perfs) * 100) if perfs else 0
                print(
                    f"  • 「{item['original']}」— 改動 {item['count']} 次（高表現佔 {high_pct}%）"
                )
        reasons = report.get("frequent_reasons", [])
        if reasons:
            print("\n📝 常見改動原因：")
            for item in reasons[:5]:
                print(f"  • {item['reason']}（{item['count']} 次）")
        trend = report.get("trend", "insufficient")
        if trend != "insufficient":
            td = report["trend_detail"]
            labels = {
                "improving": "📈 改善中",
                "worsening": "📉 變多",
                "stable": "➡️ 穩定",
            }
            print(
                f"\n趨勢：{labels.get(trend, trend)}（最近5支 avg={td['recent_avg']} vs 之前 avg={td['earlier_avg']}）"
            )


def _cmd_lessons(ctx):
    if len(sys.argv) < 3:
        print(
            "用法：video-ops.py lessons <list|add|add-evidence|stats|propose-hardening|archive> ..."
        )
        sys.exit(1)
    sub = sys.argv[2]
    operator = ctx["op_paths"]["operator"]

    if sub == "list":
        kv = _parse_kv_args(sys.argv, start=3)
        rows = query_lessons(
            operator=operator,
            origin=kv.get("origin"),
            stage=kv.get("stage"),
        )
        print(f"✅ lessons list（{len(rows)}）")
        for item in rows:
            print(
                f"  • {item.get('id')} | {item.get('origin')} | {item.get('stage')} "
                f"| {item.get('pattern')}"
            )
        return

    if sub == "add":
        kv = _parse_kv_args(sys.argv, start=3)
        pattern = (kv.get("pattern") or "").strip()
        origin = (kv.get("origin") or "").strip()
        stage = (kv.get("stage") or "soft").strip()
        if not pattern or not origin:
            print(
                '用法：video-ops.py lessons add --pattern "..." --origin <mistake|humanizer|quality|verifier|deviation|manual> [--stage soft] [--scope "generation"] [--counter-pattern "..."] [--evidence-vid VID-001] [--notes "..."]'
            )
            sys.exit(1)
        scope_raw = kv.get("scope")
        scope = []
        if scope_raw:
            scope = [x.strip() for x in scope_raw.split(",") if x.strip()]
        evidence = []
        ev = kv.get("evidence_vid")
        if ev:
            evidence = [x.strip() for x in ev.split(",") if x.strip()]
        try:
            lesson_id = add_lesson(
                operator=operator,
                origin=origin,
                pattern=pattern,
                stage=stage,
                scope=scope,
                counter_pattern=kv.get("counter_pattern"),
                evidence=evidence,
                source_note=kv.get("notes"),
            )
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(f"✅ lessons add：{lesson_id} | {origin} | {stage} | {pattern}")
        return

    if sub == "stats":
        data = lessons_stats(operator)
        print(f"✅ lessons stats：total={data['total']}")
        print("  stage 分佈：")
        for st in ("soft", "hardened", "archived"):
            print(f"    - {st}: {data['by_stage'].get(st, 0)}")
        return

    if sub == "propose-hardening":
        rows = propose_lesson_hardening(operator)
        print(f"✅ hardening 候選（soft + 有 counter_pattern）：{len(rows)}")
        for item in rows:
            print(
                f"  • {item.get('id')} | {item.get('origin')} | {item.get('pattern')}"
            )
        return

    if sub == "archive":
        if len(sys.argv) < 4:
            print('用法：video-ops.py lessons archive L-XXXX [--reason "說明"]')
            sys.exit(1)
        lesson_id = sys.argv[3]
        kv = _parse_kv_args(sys.argv, start=4)
        reason = kv.get("reason")
        ok = archive_lesson(operator, lesson_id, reason=reason)
        if not ok:
            print(f"❌ 找不到 lesson 或已 archived：{lesson_id}")
            sys.exit(1)
        suffix = f"（原因：{reason}）" if reason else ""
        print(f"✅ 已 archive：{lesson_id}{suffix}")
        return

    if sub == "add-evidence":
        if len(sys.argv) < 4:
            print("用法：video-ops.py lessons add-evidence L-XXXX --vid VID-NNN")
            sys.exit(1)
        lesson_id = sys.argv[3]
        kv = _parse_kv_args(sys.argv, start=4)
        vid = (kv.get("vid") or "").strip()
        if not vid:
            print("用法：video-ops.py lessons add-evidence L-XXXX --vid VID-NNN")
            sys.exit(1)
        try:
            result = add_lesson_evidence(operator, lesson_id, vid)
        except ValueError as e:
            print(f"❌ {e}")
            sys.exit(1)
        if not result["found"]:
            print(f"❌ lesson {lesson_id} not found", file=sys.stderr)
            sys.exit(1)
        if not result["added"]:
            print(f"✅ already in evidence: {lesson_id} has {vid}")
            return
        print(
            f"✅ lessons add-evidence: {lesson_id} += {vid} (now {result['evidence_count']} evidence)"
        )
        return

    print(
        "❌ 用法：video-ops.py lessons <list|add|add-evidence|stats|propose-hardening|archive> ..."
    )
    sys.exit(1)


def _cmd_record_mistake(ctx):
    if len(sys.argv) < 3:
        print('用法：video-ops.py 記錯 "描述" 或 video-ops.py record-mistake "描述"')
        sys.exit(1)
    description = sys.argv[2]
    lesson_id = record_mistake(
        operator=ctx["op_paths"]["operator"],
        description=description,
        correct_behavior=None,
        context="video-ops 記錯命令",
        stage="soft",
    )
    print(f"✅ 已記錯並寫入 lessons：{lesson_id}")


def _cmd_todo(ctx):
    if len(sys.argv) < 3:
        print(
            "用法：video-ops.py todo <add|list|close|reopen|archive|update|auto-close> ..."
        )
        sys.exit(1)

    sub = sys.argv[2]
    operator = ctx["op_paths"]["operator"]

    if sub == "add":
        kv = _parse_kv_args(sys.argv, start=3)
        if not kv.get("title"):
            print(
                '用法：video-ops.py todo add --title "..." [--priority high] [--due YYYY-MM-DD] [--related-vid VID-001] [--related-lesson L-0001] [--tags t1,t2] [--notes "..."]'
            )
            sys.exit(1)
        todo_id = add_todo(
            operator=operator,
            title=kv.get("title"),
            priority=kv.get("priority", "normal"),
            due=kv.get("due"),
            related_vid=kv.get("related_vid"),
            related_lesson_id=kv.get("related_lesson"),
            tags=kv.get("tags"),
            notes=kv.get("notes"),
        )
        print(f"✅ 已新增待辦：{todo_id} | {kv.get('title')}")
        return

    if sub == "list":
        kv = _parse_kv_args(sys.argv, start=3)
        rows = query_todos(
            operator=operator,
            state=kv.get("state"),
            priority=kv.get("priority"),
            due_before=kv.get("due_before"),
            tag=kv.get("tag"),
            overdue=("--overdue" in sys.argv[3:]),
        )
        print(f"📋 todos（{len(rows)}）")
        for item in rows:
            due = item.get("due") or "-"
            print(
                f"  • {item.get('id')} | {item.get('state')} | {item.get('priority')} | due={due} | {item.get('title')}"
            )
        return

    if sub == "close":
        if len(sys.argv) < 5:
            print('用法：video-ops.py todo close T-0001 --reason "完成"')
            sys.exit(1)
        todo_id = sys.argv[3]
        kv = _parse_kv_args(sys.argv, start=4)
        reason = kv.get("reason")
        if not reason:
            print("❌ close 需要 --reason")
            sys.exit(1)
        ok = close_todo(operator, todo_id, reason)
        print(f"{'✅' if ok else '❌'} {'已關閉' if ok else '找不到待辦'}：{todo_id}")
        if not ok:
            sys.exit(1)
        return

    if sub == "reopen":
        if len(sys.argv) < 4:
            print("用法：video-ops.py todo reopen T-0001")
            sys.exit(1)
        todo_id = sys.argv[3]
        ok = reopen_todo(operator, todo_id)
        print(f"{'✅' if ok else '❌'} {'已重開' if ok else '找不到待辦'}：{todo_id}")
        if not ok:
            sys.exit(1)
        return

    if sub == "archive":
        if len(sys.argv) < 5:
            print('用法：video-ops.py todo archive T-0001 --reason "擱置"')
            sys.exit(1)
        todo_id = sys.argv[3]
        kv = _parse_kv_args(sys.argv, start=4)
        reason = kv.get("reason")
        if not reason:
            print("❌ archive 需要 --reason")
            sys.exit(1)
        ok = archive_todo(operator, todo_id, reason)
        print(f"{'✅' if ok else '❌'} {'已封存' if ok else '找不到待辦'}：{todo_id}")
        if not ok:
            sys.exit(1)
        return

    if sub == "auto-close":
        dry_run = "--dry-run" in sys.argv[3:]
        todos = query_todos(operator=operator, state="pending")
        pdata = load_pipeline()
        by_vid = {it.get("vid"): it for it in pdata.get("items", []) if it.get("vid")}
        closable = []
        for row in todos:
            related = row.get("related_vid")
            if not related:
                continue
            item = by_vid.get(related)
            if not item:
                continue
            if item.get("status") == "已上線" and item.get("backfill"):
                closable.append(row.get("id"))
        if not closable:
            print("ℹ️ 無可自動關閉待辦")
            return
        for todo_id in closable:
            if dry_run:
                print(f"✓ {todo_id} 自動關閉（dry-run）")
            else:
                archive_todo(operator, todo_id, "related VID backfilled")
                print(f"✓ {todo_id} 自動關閉")
        return

    if sub == "update":
        if len(sys.argv) < 4:
            print(
                "用法：video-ops.py todo update T-0001 [--title ...] [--priority ...] [--due ...] [--tags ...] [--notes ...]"
            )
            sys.exit(1)
        todo_id = sys.argv[3]
        kv = _parse_kv_args(sys.argv, start=4)
        fields = {}
        mapping = {
            "title": "title",
            "priority": "priority",
            "due": "due",
            "tags": "tags",
            "notes": "notes",
            "related_vid": "related_vid",
            "related_lesson": "related_lesson_id",
            "state": "state",
        }
        for src, dst in mapping.items():
            if src in kv:
                fields[dst] = kv[src]
        if not fields:
            print("❌ update 至少要提供一個欄位")
            sys.exit(1)
        ok = update_todo(operator, todo_id, **fields)
        print(f"{'✅' if ok else '❌'} {'已更新' if ok else '找不到待辦'}：{todo_id}")
        if not ok:
            sys.exit(1)
        return

    print(f"❌ 未知 todo 子命令：{sub}")
    sys.exit(1)


def _cmd_retrieval(ctx):
    if len(sys.argv) < 4:
        print(
            "用法：video-ops.py retrieval similar-vids VID-NNN [--limit 5] [--include-fields f1,f2]"
        )
        sys.exit(1)
    sub = sys.argv[2]
    if sub != "similar-vids":
        print(f"❌ 未知 retrieval 子命令：{sub}")
        sys.exit(1)
    vid = sys.argv[3]
    kv = _parse_kv_args(sys.argv, start=4)
    try:
        limit = int(kv.get("limit", 5))
    except (ValueError, TypeError):
        print("❌ --limit 需為整數")
        sys.exit(1)
    include_fields = [
        x.strip()
        for x in kv.get(
            "include_fields", "hook_type,verifier_scores,actual_views,deviation_score"
        ).split(",")
        if x.strip()
    ]
    try:
        rows = get_similar_vids(
            vid=vid,
            limit=limit,
            include_fields=include_fields,
            operator=ctx["op_paths"]["operator"],
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}")
        sys.exit(1)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def _fix_learning_field(data):
    """修復 learning_extracted=true 但缺 learning 欄位的歷史資料。"""
    fixed = []
    for v in data.get("videos", []):
        vid = v.get("vid")
        bf = v.get("backfill") or {}
        if not bf.get("learning_extracted"):
            continue
        if v.get("learning"):
            continue

        sp = (v.get("script_path") or "").strip()
        level = bf.get("performance", "normal")
        if sp and (PROJECT_ROOT / sp).exists():
            # 盡力自動補齊：高表現用 auto_extract 猜 opening/cta；其他型別回填 skipped 標記
            if level == "high":
                extracted = auto_extract_from_script(sp)
                opening = (extracted or {}).get("opening_guess")
                cta = (extracted or {}).get("cta_guess")
                if opening or cta:
                    ok, _ = extract_learning(
                        data,
                        vid,
                        opening=opening,
                        cta=cta,
                        hook=(extracted or {}).get("hook"),
                    )
                    if ok:
                        fixed.append((vid, "extract-learning"))
                        continue
            v["learning"] = {
                "extracted_date": today_str(),
                "type": "skipped-auto-migrate",
                "reason": "legacy learning_extracted=true but missing learning",
            }
            fixed.append((vid, "mark-skipped"))
        else:
            bf["learning_extracted"] = False
            v["backfill"] = bf
            fixed.append((vid, "set-learning_extracted-false"))
    return fixed


def _cmd_health(ctx):
    """大腦健康度單行可視化（per-dimension 原始數字、不算 overall score）。"""
    from lib.health import compute_health, format_health_report

    operator = ctx["op_paths"]["operator"]
    report = format_health_report(compute_health(operator))
    print(report)


SIMPLE_COMMAND_HANDLERS = {
    "list": _cmd_list,
    "get": _cmd_get,
    "next-vid": _cmd_next_vid,
    "add": _cmd_add,
    "transition": _cmd_transition,
    "delete": _cmd_delete,
    "bind-script": _cmd_bind_script,
    "list-orphans": _cmd_list_orphans,
    "update-date": _cmd_update_date,
    "set-hook-type": _cmd_set_hook_type,
    "add-transcript": _cmd_add_transcript,
    "quick-add": _cmd_quick_add,
    "batch-quick-add": _cmd_batch_quick_add,
    "query-pending-scripts": _cmd_query_pending_scripts,
    "add-idea": _cmd_add_idea,
    "list-ideas": _cmd_list_ideas,
    "transition-idea": _cmd_transition_idea,
    "confirm": _cmd_confirm,
    "save": _cmd_save,
    "adoption-stats": _cmd_adoption_stats,
    "convert-idea": _cmd_convert_idea,
    "backfill": _cmd_backfill,
    "extract-learning": _cmd_extract_learning,
    "cleanup-formulas": _cmd_cleanup_formulas,
    "record-deviation": _cmd_record_deviation,
    "diff-script": _cmd_diff_script,
    "analyze-deviations": _cmd_analyze_deviations,
    "lessons": _cmd_lessons,
    "record-mistake": _cmd_record_mistake,
    "記錯": _cmd_record_mistake,
    "todo": _cmd_todo,
    "retrieval": _cmd_retrieval,
    "health": _cmd_health,
}


# ── CLI 主程式 ────────────────────────────────────────────


def _extract_operator(argv):
    """從 argv 中提取 --operator 參數並移除。回傳 (operator, cleaned_argv)。"""
    cleaned = []
    operator = DEFAULT_OPERATOR
    i = 0
    while i < len(argv):
        if argv[i] == "--operator" and i + 1 < len(argv):
            operator = argv[i + 1].lower()
            if operator not in VALID_OPERATORS:
                print(
                    f"❌ 未知操作員：{operator}（合法值：{', '.join(sorted(VALID_OPERATORS))}）"
                )
                sys.exit(1)
            i += 2
        else:
            cleaned.append(argv[i])
            i += 1
    return operator, cleaned


def main():
    # 強制 UTF-8 輸出：Windows / 非 UTF-8 locale 下，含中文 + emoji 的輸出被 pipe /
    # 重導 / 程式捕捉時，預設 locale codec（如 cp950）無法編碼 emoji → print 中途崩潰
    # （半輸出 + 非零 exit、看似失敗實則操作可能已半執行）。在此移除對 PYTHONIOENCODING
    # 的依賴、讓 CLI 在所有平台輸出一致。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    # 提取 --operator 全域參數
    operator, cleaned_argv = _extract_operator(sys.argv)
    sys.argv = cleaned_argv  # 替換 argv 讓後續指令解析不受影響
    set_operator(operator)
    op_paths = get_operator_paths(operator)
    op_label = op_paths["label"]

    if operator != DEFAULT_OPERATOR:
        print(f"👤 操作員：{op_label}（{op_paths['vid_prefix']}-NNN）")

    cmd = sys.argv[1]
    data = load_tracking()

    # ── 影片操作 ──────────────────────────────────────────

    simple_handler = SIMPLE_COMMAND_HANDLERS.get(cmd)
    if simple_handler:
        simple_handler({"data": data, "op_paths": op_paths})
        return

    # ── 靈感操作（pipeline 統一管線）──────────────────────

    # ── 回填操作 ──────────────────────────────────────────

    # ── 選題去重 ────────────────────────────────────────────

    if cmd == "list-topics":
        pdata = load_pipeline()
        status_icons = {
            "inbox": "📥",
            "selected": "⭐",
            "cooldown": "❄️",
            "待拍": "📋",
            "剪輯中": "✂️",
            "已上線": "✅",
            "archived": "🗄️",
        }
        # 影片階段
        videos = [i for i in pdata["items"] if i.get("vid")]
        print("━━ 🎬 影片 ━━")
        for v in videos:
            icon = status_icons.get(v["status"], "?")
            title_note = f"｜標題：{v['title']}" if v.get("title") else ""
            print(f"  {icon} {v['vid']} | {v['status']} | {v['topic']}{title_note}")
        if not videos:
            print("  （無）")
        # 靈感階段
        ideas = [
            i
            for i in pdata["items"]
            if i["status"] in ("inbox", "selected", "cooldown")
        ]
        print("\n━━ 💡 靈感 ━━")
        for idea in ideas:
            icon = status_icons.get(idea["status"], "?")
            print(f"  {icon} {idea['idea_id']} | {idea['status']:9s} | {idea['topic']}")
        if not ideas:
            print("  （無）")
        print(f"\n📊 已佔用：{len(videos)} 支影片 + {len(ideas)} 條靈感")
        print("⚠️ 生成新選題/標題時，須排除以上主題（含語意相近的變體）")

    # ── 驗證 + 遷移 ──────────────────────────────────────

    elif cmd == "validate":
        warnings = []
        errors = validate(data, warnings=warnings)
        if warnings:
            print(f"⚠️ 警告（{len(warnings)} 項）：")
            for w in warnings:
                print(f"  • {w}")
        if errors:
            print(f"❌ 驗證失敗（{len(errors)} 個問題）：")
            for e in errors:
                print(f"  • {e}")
            sys.exit(1)
        else:
            print(
                f"✅ 驗證通過（{len(data['videos'])} 支影片，{len(warnings)} 項警告）"
            )

    elif cmd == "validate-all":
        auto_migrate = "--auto-migrate" in sys.argv
        result = validate_all(data)
        _print_validate_all(data, result)
        # migrate 建議
        mc = result.get("migrate_candidates", [])
        if mc:
            if auto_migrate:
                mr = migrate(data)
                changes = mr["migrated"]
                if changes:
                    save_tracking(data)
                    print(f"\n🔧 auto-migrate：已補齊 {len(changes)} 個欄位")
                    for c in changes:
                        print(f"  • {c['vid']}：{c['field']}")
            else:
                total_fields = sum(len(fields) for _, fields in mc)
                print(
                    f"\n💡 {len(mc)} 支影片可跑 migrate 補齊 {total_fields} 個欄位（加 --auto-migrate 自動修復）"
                )
        drifts = collect_schema_drifts()
        b = [d for d in drifts if d["level"] == "breaking"]
        nb = [d for d in drifts if d["level"] == "non-breaking"]
        info = [d for d in drifts if d["level"] == "info"]
        print(
            f"\n🔍 Schema drift: {len(b)} breaking, {len(nb)} non-breaking, {len(info)} info"
        )
        for d in b:
            print(f"❌ BREAKING: {d['file']} {d['field']} {d['detail']}")
        for d in nb:
            print(f"⚠️ NON-BREAKING: {d['file']} {d['field']} {d['detail']}")
        if b:
            sys.exit(1)

    elif cmd == "renumber":
        dry_run = "--dry-run" in sys.argv
        vid_map = renumber_videos(
            data, vid_prefix=op_paths["vid_prefix"], dry_run=dry_run
        )
        if not vid_map:
            print("✅ VID 編號已按 publish_date 排序，無需重新編號")
        elif dry_run:
            print(f"🧪 renumber dry-run（{len(vid_map)} 支將變更）：")
            for old_vid, new_vid in sorted(vid_map.items(), key=lambda x: x[1]):
                print(f"  {old_vid} → {new_vid}")
        else:
            print(f"✅ 重新編號完成（{len(vid_map)} 支影片變更）：")
            for old_vid, new_vid in sorted(vid_map.items(), key=lambda x: x[1]):
                print(f"  {old_vid} → {new_vid}")
            print("\n🔍 重新編號後驗證：")
            data = load_tracking()
            result = validate_all(data)
            _print_validate_all(data, result)

    elif cmd == "migrate":
        fix_learning = "--fix-learning-field" in sys.argv
        result = migrate(data)
        changes = result["migrated"]
        learning_changes = []
        if fix_learning:
            learning_changes = _fix_learning_field(data)
        if not changes:
            if learning_changes:
                save_tracking(data)
                print(f"✅ learning 欄位修復完成（{len(learning_changes)} 支）")
                for vid, action in learning_changes:
                    print(f"  • {vid}：{action}")
            else:
                print("✅ 所有影片欄位已完整，無需遷移")
        else:
            save_tracking(data)
            vids_changed = {}
            for c in changes:
                vids_changed.setdefault(c["vid"], []).append(c["field"])
            print(
                f"✅ 遷移完成（{len(vids_changed)} 支影片，{len(changes)} 個欄位補齊）："
            )
            for vid, fields in vids_changed.items():
                print(f"  • {vid}：{', '.join(fields)}")
            print("\n🔍 遷移後驗證：")
            warnings = []
            errors = validate(data, warnings=warnings)
            if errors:
                print(f"  ❌ 仍有 {len(errors)} 個問題：")
                for e in errors:
                    print(f"    • {e}")
            else:
                print(f"  ✅ 驗證通過（{len(data['videos'])} 支影片）")
            if learning_changes:
                print(f"\n🧩 learning 欄位修復（{len(learning_changes)} 支）：")
                for vid, action in learning_changes:
                    print(f"  • {vid}：{action}")

    elif cmd == "pipeline-stats":
        pdata = load_pipeline()
        stats = pipeline_stats(pdata)
        sc = stats["status_counts"]
        print("📊 轉化漏斗")
        print(f"  總靈感數：{stats['total_ideas']}")
        print(
            f"  📥 inbox: {sc.get('inbox', 0)}  ⭐ selected: {sc.get('selected', 0)}  ❄️ cooldown: {sc.get('cooldown', 0)}  🗄️ archived: {stats['archived']}"
        )
        print(
            f"  📋 待拍: {sc.get('待拍', 0)}  ✂️ 剪輯中: {sc.get('剪輯中', 0)}  ✅ 已上線: {stats['published']}  📊 已回填: {stats['backfilled']}"
        )
        print()
        print("📈 轉化率")
        print(
            f"  靈感 → 影片：{stats['idea_to_vid_pct']}%（{stats['has_vid']}/{stats['total_ideas']}）"
        )
        print(
            f"  影片 → 上線：{stats['vid_to_publish_pct']}%（{stats['published']}/{stats['has_vid']}）"
        )
        print(
            f"  靈感 → 上線：{stats['idea_to_publish_pct']}%（{stats['published']}/{stats['total_ideas']}）"
        )
        if stats["avg_cycle_days"] is not None:
            print(
                f"\n⏱️ 平均週期：{stats['avg_cycle_days']} 天（靈感→上線，樣本 {stats['cycle_sample_size']} 支）"
            )
        if stats["longest_wait"]:
            lw = stats["longest_wait"]
            print(f"\n⚠️ 等最久：{lw['vid']}「{lw['topic']}」已等 {lw['days']} 天")

    elif cmd == "record-verifier-scores":
        quiet = "--quiet" in sys.argv
        argv = _argv_without_flags(sys.argv, ["--quiet"])
        if len(argv) < 3:
            print(
                "用法：video-ops.py record-verifier-scores VID-NNN --conflict-score N --retention-prediction LEVEL --ai-residue-count N --data-consistency true|false --format-complete true|false --pass-count N/5 [--quiet]"
            )
            sys.exit(1)
        vid = argv[2]
        kv = _parse_kv_args(argv, start=3)
        invalid_positional = [v for k, v in kv.items() if k.startswith("_pos_")]
        if invalid_positional:
            print(f"❌ 無法解析的參數：{' '.join(invalid_positional)}")
            sys.exit(1)
        allowed_keys = {
            "conflict_score",
            "retention_prediction",
            "ai_residue_count",
            "data_consistency",
            "format_complete",
            "pass_count",
            "from_stdin",
        }
        unknown_keys = sorted(k for k in kv.keys() if k not in allowed_keys)
        if unknown_keys:
            unknown_flags = ", ".join(f"--{k.replace('_', '-')}" for k in unknown_keys)
            print(f"❌ 不支援的參數：{unknown_flags}")
            sys.exit(1)
        scores = {}
        if "from_stdin" in kv:
            scores = _load_json_object_from_stdin("--from-stdin")
        if "conflict_score" in kv:
            try:
                scores["conflict_score"] = int(kv["conflict_score"])
            except ValueError:
                print("❌ conflict_score 必須為整數")
                sys.exit(1)
        if "retention_prediction" in kv:
            scores["retention_prediction"] = kv["retention_prediction"]
        if "ai_residue_count" in kv:
            try:
                scores["ai_residue_count"] = int(kv["ai_residue_count"])
            except ValueError:
                print("❌ ai_residue_count 必須為整數")
                sys.exit(1)
        if "data_consistency" in kv:
            parsed, err = _parse_bool_arg(kv["data_consistency"], "data_consistency")
            if err:
                print(f"❌ {err}")
                sys.exit(1)
            scores["data_consistency"] = parsed
        if "format_complete" in kv:
            parsed, err = _parse_bool_arg(kv["format_complete"], "format_complete")
            if err:
                print(f"❌ {err}")
                sys.exit(1)
            scores["format_complete"] = parsed
        if "pass_count" in kv:
            scores["pass_count"] = kv["pass_count"]
        if "from_stdin" not in kv:
            required_flags = {
                "conflict_score": "--conflict-score",
                "retention_prediction": "--retention-prediction",
                "ai_residue_count": "--ai-residue-count",
                "data_consistency": "--data-consistency",
                "format_complete": "--format-complete",
                "pass_count": "--pass-count",
            }
            missing_flags = [
                flag for key, flag in required_flags.items() if key not in scores
            ]
            if missing_flags:
                print(f"❌ 缺少必填參數：{', '.join(missing_flags)}")
                sys.exit(1)
        ok_validate, normalized_or_msg = validate_verifier_scores(scores)
        if not ok_validate:
            print(f"❌ {normalized_or_msg}")
            sys.exit(1)
        scores = normalized_or_msg
        ok, msg = record_verifier_scores(data, vid, scores)
        if not ok:
            print(f"❌ {msg}")
            sys.exit(1)
        if not quiet:
            _print_verifier_stdout_summary(vid, scores, msg)

    else:
        print(f"未知指令：{cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
