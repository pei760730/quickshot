#!/usr/bin/env python3
"""reset-operator.py — bootstrap-client.sh 的 Python helper

v4.38 架構：operator 定義改存 data/.operators.json（blacklist 保護、sync-engine 不覆蓋），
不再修改 scripts/ops/lib/config.py（引擎檔、會被同步覆蓋）。

做四件事：
1. 寫 data/.operators.json 註冊新 operator（包含 data_dir_rel / vid_prefix / label 等）
2. 建立 CLAUDE.local.md（客戶品牌身份）
3. 更新 README.md 的品牌名
4. 在 engine-manifest.json 記錄客戶初始化資訊（_meta.client）

用法（由 bootstrap-client.sh 呼叫）：
  python3 scripts/bootstrap/reset-operator.py --operator long-bro --brand "長兄 OS" --init-date 2026-04-21
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def write_operators_json(operator: str, brand: str, init_date: str):
    """寫 data/.operators.json 註冊新 operator（取代原本改 config.py 的做法）。

    此檔在 engine-manifest._meta.sync_blacklist 的 data/** 規則下、
    會被 sync-engine 跳過、不會被引擎覆蓋。客戶的 operator 定義永久保留。
    """
    path = ROOT / "data" / ".operators.json"
    entry = {
        "display_name": operator.title().replace("-", " ").replace("_", " "),
        "brand": brand,
        "data_dir_rel": f"data/{operator}",
        "production_dir_rel": "03-production-line",
        "enabled": True,
        "created_at": init_date,
    }

    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {
            "schema_version": "1.0",
            "description": "Per-repo operator registry — sync-engine 不覆蓋此檔",
            "operators": {},
        }

    operators = payload.setdefault("operators", {})
    if operator in operators:
        print(f"   ⚠️ data/.operators.json：{operator} 已存在，跳過註冊")
        return
    operators[operator] = entry

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"   data/.operators.json：註冊 {operator}")


def create_claude_local(brand: str, operator: str, init_date: str):
    """從 template/CLAUDE.local.md 建立客戶專屬身份設定檔。

    CLAUDE.md 本身不再被動到（引擎通用版），客戶品牌名 / operator / 使用者習慣
    都集中在 CLAUDE.local.md，sync-engine 永不覆蓋。
    """
    template = ROOT / "01-data-brain" / "template" / "CLAUDE.local.md"
    target = ROOT / "CLAUDE.local.md"
    if not template.exists():
        print("   ⏭️ template/CLAUDE.local.md 不存在，跳過")
        return

    # 取引擎版本號（從 engine-manifest 讀）
    manifest_path = ROOT / "engine-manifest.json"
    engine_version = "unknown"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        engine_version = m.get("_meta", {}).get("engine_version", "unknown")

    # operator label：優先用 operator 轉 title case
    operator_label = operator.replace("-", " ").replace("_", " ").title()

    text = template.read_text(encoding="utf-8")
    text = (
        text
        .replace("{{BRAND_NAME}}", brand)
        .replace("{{OPERATOR_KEY}}", operator)
        .replace("{{OPERATOR_LABEL}}", operator_label)
        .replace("{{ENGINE_VERSION}}", f"v{engine_version}")
        .replace("{{INIT_DATE}}", init_date)
    )
    target.write_text(text, encoding="utf-8")
    print(f"   CLAUDE.local.md：建立完成（品牌 {brand}、operator {operator}）")


def update_readme(brand: str):
    path = ROOT / "README.md"
    if not path.exists():
        print("   ⏭️ README.md 不存在，跳過")
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("Red Tea Bus", brand).replace("紅茶巴士", brand)
    path.write_text(text, encoding="utf-8")
    print(f"   README.md：品牌名更新為 {brand}")


def update_manifest(operator: str, brand: str, init_date: str):
    path = ROOT / "engine-manifest.json"
    if not path.exists():
        print("   ⏭️ engine-manifest.json 不存在，跳過")
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    engine_version = manifest.get("_meta", {}).get("engine_version", "unknown")

    manifest["_meta"]["client"] = {"name": operator, "brand": brand, "repo_type": "engine+client"}

    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"   engine-manifest.json：記錄客戶 {brand}（從引擎 v{engine_version} 初始化）")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--init-date", required=True)
    args = parser.parse_args()

    print(f"   更新 operators/CLAUDE.local/README/manifest（operator={args.operator}, brand={args.brand}）")
    write_operators_json(args.operator, args.brand, args.init_date)
    create_claude_local(args.brand, args.operator, args.init_date)
    update_readme(args.brand)
    update_manifest(args.operator, args.brand, args.init_date)


if __name__ == "__main__":
    main()
