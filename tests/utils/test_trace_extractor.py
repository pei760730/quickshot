import json

from scripts.utils.lib import trace_extractor
from scripts.utils.lib.trace_extractor import extract_trace_payload, infer_vid


def test_extract_verifier_scores_only():
    text = '```json\n{"verifier_scores":{"conflict_score":8}}\n```'
    assert extract_trace_payload(text) == {"verifier_scores": {"conflict_score": 8}}


def test_ignore_malformed_json_fence():
    text = '```json\n{"verifier_scores":\n```'
    assert extract_trace_payload(text) is None


def test_multiple_fences_merge_supported_fields():
    text = (
        '```json\n{"foo":1}\n```\n'
        '```json\n{"bar":2}\n```\n'
        '```json\n{"verifier_scores":{"b":2}}\n```\n'
    )
    assert extract_trace_payload(text) == {
        "verifier_scores": {"b": 2},
    }


def test_no_fence_returns_none():
    assert extract_trace_payload('{"verifier_scores": {"a": 1}}') is None


def test_vid_inference_miss_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(trace_extractor, "ADOPTION_STATS_DIR", tmp_path)
    monkeypatch.setattr(trace_extractor, "VID_INFERENCE_LOG", tmp_path / "vid_inference.jsonl")
    infer_vid('```json\n{"verifier_scores":{"pass_count":"5/5"}}\n```', env={})
    lines = (tmp_path / "vid_inference.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["had_fenced"] is True
    assert row["vid_inferred"] is False


def test_no_fenced_block_does_not_write_vid_inference(tmp_path, monkeypatch):
    monkeypatch.setattr(trace_extractor, "ADOPTION_STATS_DIR", tmp_path)
    monkeypatch.setattr(trace_extractor, "VID_INFERENCE_LOG", tmp_path / "vid_inference.jsonl")
    infer_vid('{"verifier_scores":{"pass_count":"5/5"}}', env={})
    assert not (tmp_path / "vid_inference.jsonl").exists()
