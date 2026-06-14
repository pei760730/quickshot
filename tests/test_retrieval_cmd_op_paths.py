"""retrieval similar-vids 的 op_paths key 守門。

曾經 _cmd_retrieval 索引 ctx["op_paths"]["tracking_json"]、但這個 key 全 repo
從沒被設定過（get_operator_paths 只給 pipeline_json / operator）→ 指令直接 KeyError，
且 except 只接 ValueError 接不住。現改用 operator-based 解析。
"""

import sys

import pytest
from path_bootstrap import load_video_ops_module


def test_op_paths_has_no_phantom_tracking_json_key():
    """守住別再用幽靈 key：get_operator_paths 有 operator、沒有 tracking_json。"""
    mod = load_video_ops_module()
    op_paths = mod.get_operator_paths("default")
    assert "operator" in op_paths
    assert "tracking_json" not in op_paths


def test_retrieval_cmd_graceful_on_missing_vid(monkeypatch):
    """retrieval similar-vids 找不到 VID 時應優雅 SystemExit(1)、不是 KeyError。"""
    mod = load_video_ops_module()
    ctx = {"op_paths": mod.get_operator_paths("default")}
    monkeypatch.setattr(
        sys,
        "argv",
        ["video-ops.py", "retrieval", "similar-vids", "VID-NONEXIST-999"],
    )
    with pytest.raises(SystemExit) as exc:
        mod._cmd_retrieval(ctx)
    assert exc.value.code == 1
