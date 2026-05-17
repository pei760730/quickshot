"""Semantic dedup guard for lessons.json.

Regression guard for 2026-04-21 scan: legacy `claude-mistakes.json` + `generation-rules.json`
both held entries for the same underlying rule (e.g. "請補充" 偵測 recorded once in
claude-mistakes graduated, once in generation-rules avoid_patterns). The
migration script writes both paths to `lessons.json` but its dedup key is
`(origin, pattern)` — slightly different wording on the two sides produced
twin `graduated_mistake` rows (L-0001↔L-0008, L-0002↔L-0009, L-0007↔L-0010).

This test pins the current archived resolution: for each known dup signature
there must be **at most one** non-archived lesson. If a future migration or
manual add re-introduces a near-duplicate, CI fails here and forces the
operator to archive or merge.

Scope: kai operator only (the only operator with migrated legacy data as of
v4.43). Extend to other operators if they ever migrate legacy files.
"""

import json
from pathlib import Path

import pytest


# Keyword signatures for pattern-groups that previously duplicated during
# migration. A lesson is considered a "hit" for a signature iff every keyword
# in the signature appears in the pattern string. Reviewed 2026-04-21.
_DUP_SIGNATURES = [
    ("請補充_生成", ("請補充", "生成")),
    ("虛構_案例", ("虛構", "案例")),
    ("API_假設", ("API", "假設")),
]


def _repo_root():
    return Path(__file__).resolve().parent.parent


@pytest.mark.skipif(
    not (Path(__file__).resolve().parent.parent / "data" / "kai" / "lessons.json").exists(),
    reason="kai-only scope (migrated legacy data per v4.43)",
)
def test_no_semantic_duplicate_active_lessons():
    lessons_path = _repo_root() / "data" / "kai" / "lessons.json"
    assert lessons_path.exists(), f"lessons.json 不存在：{lessons_path}"

    payload = json.loads(lessons_path.read_text(encoding="utf-8"))
    non_archived = [
        row for row in payload.get("lessons", [])
        if row.get("stage") != "archived"
    ]

    failures = []
    for sig_name, keywords in _DUP_SIGNATURES:
        matches = [
            row for row in non_archived
            if all(kw in (row.get("pattern") or "") for kw in keywords)
        ]
        if len(matches) > 1:
            ids = [row.get("id") for row in matches]
            failures.append(
                f"signature={sig_name} keywords={keywords} "
                f"→ {len(matches)} non-archived matches: {ids}"
            )

    assert not failures, (
        "lessons.json 出現語意重複的 active/observation/candidate lesson：\n  "
        + "\n  ".join(failures)
        + "\n解決：archive 較弱版本或合併 evidence（見 docs/contracts/lessons-schema.md §去重規則）"
    )
