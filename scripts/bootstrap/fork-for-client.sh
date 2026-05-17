#!/usr/bin/env bash
# fork-for-client.sh — 從主 repo 分叉出純客戶 repo
#
# 與 bootstrap-client.sh 的分工：
#   bootstrap-client.sh  在現有 repo 新增 operator（純加法、適合 multi-operator 場景）
#   fork-for-client.sh   從主 repo 分叉出獨立客戶 repo（clone + purge 其他 operator + 跑 bootstrap）
#
# 解決問題：新客戶 repo（例：KaiOS-Client-LongBroOS）若直接 clone 主 repo 會帶著
# 主 repo 的客戶資料（Kai 紅茶巴士 / 歷史腳本 / 訪談原文等），造成「污染化石」。
# 本腳本確保 target repo 起始狀態只有引擎 + template、不帶任何既有客戶資料。
#
# 用法：
#   bash scripts/bootstrap/fork-for-client.sh <operator> <brand> <target_dir> [flags]
#
# 例子：
#   bash scripts/bootstrap/fork-for-client.sh longbro "龍OS" ../KaiOS-Client-LongBroOS
#
# Flags：
#   --dry-run          只列會做、不真做
#   --fresh-history    clone 後 rm -rf .git && git init（隔離 history、新 repo）
#   --from <path>      source repo 位置（預設當前 repo）
#   --yes              跳過 Purge 前的 Enter 確認（CI 用、預設互動）

set -euo pipefail

# ---------- 參數解析 ----------
OPERATOR=""
BRAND=""
TARGET=""
DRY_RUN=0
FRESH_HISTORY=0
YES=0
SOURCE=""

positional=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --fresh-history) FRESH_HISTORY=1; shift ;;
    --yes) YES=1; shift ;;
    --from) SOURCE="$2"; shift 2 ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# //'
      exit 0
      ;;
    --*) echo "❌ 未知 flag：$1" >&2; exit 1 ;;
    *) positional+=("$1"); shift ;;
  esac
done

if [[ ${#positional[@]} -lt 3 ]]; then
  echo "用法：bash scripts/bootstrap/fork-for-client.sh <operator> <brand> <target_dir> [flags]" >&2
  echo "跑 --help 看完整選項" >&2
  exit 1
fi

OPERATOR="${positional[0]}"
BRAND="${positional[1]}"
TARGET="${positional[2]}"

# operator 合法性：字母數字 + dash + underscore
if [[ ! "$OPERATOR" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "❌ operator 只能包含 [a-zA-Z0-9_-]：$OPERATOR" >&2
  exit 1
fi

# source 預設當前 repo
if [[ -z "$SOURCE" ]]; then
  SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
SOURCE="$(cd "$SOURCE" && pwd)"

# target 防呆：必須不存在、且不能是 source 本身或子目錄
TARGET_ABS="$(cd "$(dirname "$TARGET")" 2>/dev/null && pwd)/$(basename "$TARGET")" || {
  TARGET_ABS="$TARGET"
}
if [[ -e "$TARGET_ABS" ]]; then
  echo "❌ target 已存在：$TARGET_ABS" >&2
  exit 1
fi
case "$TARGET_ABS" in
  "$SOURCE"|"$SOURCE"/*)
    echo "❌ target 不能是 source 或其子目錄（source=$SOURCE）" >&2
    exit 1
    ;;
esac

# ---------- 工具函式 ----------
run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    local msg="$*"
    # dry-run 在 source 上列檔、輸出顯示 target 路徑以避免誤解
    msg="${msg//$SOURCE/$TARGET_ABS}"
    echo "  [DRY] $msg"
  else
    eval "$@"
  fi
}

rm_if_exists() {
  local path="$1"
  if [[ -e "$path" || -L "$path" ]]; then
    run "rm -rf \"$path\""
  fi
}

purge_subdirs_except() {
  local parent="$1"; shift
  local keep=("$@")
  if [[ ! -d "$parent" ]]; then return; fi
  local entry
  for entry in "$parent"/*; do
    [[ -e "$entry" ]] || continue
    local base
    base="$(basename "$entry")"
    local keep_it=0
    local k
    for k in "${keep[@]}"; do
      [[ "$base" == "$k" ]] && keep_it=1 && break
    done
    if [[ $keep_it -eq 0 ]]; then
      run "rm -rf \"$entry\""
    fi
  done
}

header() {
  echo ""
  echo "▶ $*"
}

# ---------- 主流程 ----------
MODE="執行"
[[ $DRY_RUN -eq 1 ]] && MODE="DRY-RUN"

cat <<EOF

=== fork-for-client.sh（$MODE） ===
  operator      : $OPERATOR
  brand         : $BRAND
  source        : $SOURCE
  target        : $TARGET_ABS
  fresh-history : $([[ $FRESH_HISTORY -eq 1 ]] && echo yes || echo no)
EOF

# 確認
if [[ $DRY_RUN -eq 0 && $YES -eq 0 ]]; then
  read -r -p $'\n此操作會 clone source 到 target、並刪除 target 內所有既有 operator 資料。確認繼續？[y/N] ' ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "取消。"; exit 0 ;;
  esac
fi

# [1] Clone
header "[1] Clone source → target"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  [DRY] git clone \"$SOURCE\" \"$TARGET_ABS\""
else
  git clone "$SOURCE" "$TARGET_ABS"
fi

# 後續所有操作改在 target 上
if [[ $DRY_RUN -eq 1 ]]; then
  # dry-run 模式：沿用 source 內容列出會動的檔（結構相同）
  WORK="$SOURCE"
else
  WORK="$TARGET_ABS"
  cd "$WORK"
fi

# [2] Fresh history（opt-in）
if [[ $FRESH_HISTORY -eq 1 ]]; then
  header "[2] Fresh history：rm -rf .git && git init"
  run "rm -rf \"$WORK/.git\""
  run "cd \"$WORK\" && git init -q && git add -A && git commit -q -m 'chore: initial fork from KaiOS engine'"
fi

# [3] Purge data/ 的其他 operator 資料（保留 template / .operators.json / .cache）
header "[3] Purge data/ 客戶資料（保留 template、.operators.json、.cache）"
if [[ -d "$WORK/data" ]]; then
  # 保留清單：template、.operators.json、.cache、.gitkeep
  # 其他全 purge（kai/、employee-backup/ 等都屬客戶資料；skill-memory/ 已 v4.76 退役）
  for entry in "$WORK/data"/* "$WORK/data"/.[!.]*; do
    [[ -e "$entry" ]] || continue
    local_base="$(basename "$entry")"
    case "$local_base" in
      template|.operators.json|.cache|.gitkeep) continue ;;
      *) run "rm -rf \"$entry\"" ;;
    esac
  done
fi

# [4] Purge 01-data-brain/ 的品牌資料（保留 index.md、README.md、template/、transcripts 目錄）
header "[4] Purge 01-data-brain/ 品牌資料"
rm_if_exists "$WORK/01-data-brain/brand.md"
rm_if_exists "$WORK/01-data-brain/cases.md"
rm_if_exists "$WORK/01-data-brain/interview-bank.md"
# transcripts/ 清內容、保留目錄
if [[ -d "$WORK/01-data-brain/transcripts" ]]; then
  for f in "$WORK/01-data-brain/transcripts"/*.md; do
    [[ -e "$f" ]] || continue
    [[ "$(basename "$f")" == "README.md" ]] && continue
    run "rm -f \"$f\""
  done
fi

# [5] Purge 03-production-line/ 客戶腳本
header "[5] Purge 03-production-line/ 客戶腳本"
for stage_dir in "$WORK/03-production-line/02-ready-to-shoot" "$WORK/03-production-line/03-done"; do
  [[ -d "$stage_dir" ]] || continue
  for sub in "$stage_dir"/*; do
    [[ -e "$sub" ]] || continue
    local_base="$(basename "$sub")"
    # 保留 README.md、template/
    case "$local_base" in
      README.md|template) continue ;;
      *)
        if [[ -d "$sub" ]]; then
          run "rm -rf \"$sub\""
        fi
        ;;
    esac
  done
done

# [6] Reset data/.operators.json 為空 registry
header "[6] Reset data/.operators.json → 空 registry"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  [DRY] 寫入 $TARGET_ABS/data/.operators.json：空 operators dict"
else
  mkdir -p "$WORK/data"
  cat > "$WORK/data/.operators.json" <<'JSON'
{
  "schema_version": "1.0",
  "description": "Per-repo operator registry — sync-engine 不覆蓋此檔",
  "operators": {}
}
JSON
fi

# [7] Reset engine-manifest._meta.client → null（bootstrap 會寫回）
header "[7] Reset engine-manifest._meta.client"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  [DRY] engine-manifest.json: _meta.client = null"
else
  python3 - "$WORK/engine-manifest.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    m = json.load(f)
m.setdefault("_meta", {})["client"] = None
with open(path, "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"  engine-manifest._meta.client 已 reset")
PY
fi

# [8] Reset CLAUDE.local.md（bootstrap 會從 template 重建）
header "[8] Reset CLAUDE.local.md（bootstrap 會從 template 重建）"
rm_if_exists "$WORK/CLAUDE.local.md"

# [9] 跑 bootstrap-client.sh 初始化 target operator
header "[9] bootstrap-client.sh $OPERATOR \"$BRAND\""
if [[ $DRY_RUN -eq 1 ]]; then
  echo "  [DRY] bash $TARGET_ABS/scripts/bootstrap/bootstrap-client.sh $OPERATOR \"$BRAND\""
  echo "        → 會建 data/$OPERATOR/、CLAUDE.local.md、更新 .operators.json + manifest.client"
else
  (cd "$WORK" && bash scripts/bootstrap/bootstrap-client.sh "$OPERATOR" "$BRAND")
fi

# [10] 結束報告
header "[10] 完成"
if [[ $DRY_RUN -eq 1 ]]; then
  cat <<EOF

  DRY-RUN 模擬完畢、無任何實際檔案變動。
  實際執行請去掉 --dry-run：
    bash scripts/bootstrap/fork-for-client.sh $OPERATOR "$BRAND" $TARGET
EOF
else
  cat <<EOF

  ✅ target repo 已建於：$TARGET_ABS
  operator=$OPERATOR  brand=$BRAND

  下一步（手動）：
    cd $TARGET_ABS
    git remote remove origin           # 移除指向 source 的 origin
    git remote add origin <new-url>    # 設定新 repo remote
    git push -u origin main            # 推上去
EOF
fi
