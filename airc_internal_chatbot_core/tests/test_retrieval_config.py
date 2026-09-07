"""Unit tests for search_mode merge and similarity threshold."""
import importlib.util
from pathlib import Path

_mod_path = Path(__file__).resolve().parents[1] / "app" / "services" / "retrieval_merge.py"
_spec = importlib.util.spec_from_file_location("retrieval_merge", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
rrf_merge = _mod.rrf_merge
apply_score_threshold = _mod.apply_score_threshold


def _chunk(i, text="t"):
    return {"id": str(i), "file_id": "f1", "chunk_index": i, "text": text}


def test_rrf_merge_ranks_overlap_higher():
    vector = [(_chunk(1), 0.9, "vector"), (_chunk(2), 0.8, "vector")]
    keyword = [(_chunk(2), None, "keyword"), (_chunk(3), None, "keyword")]
    merged = rrf_merge(vector, keyword)
    ids = [c["id"] for c, _, _, _ in merged]
    assert ids[0] == "2"


def test_threshold_keeps_keyword_and_strong_vector():
    groups = [{
        "results": [
            {"origin": "vector", "vector_score": 0.8, "score": 0.8},
            {"origin": "vector", "vector_score": 0.2, "score": 0.2},
            {"origin": "keyword", "score": 0.03},
        ]
    }]
    apply_score_threshold(groups, 0.5)
    origins = [r["origin"] for r in groups[0]["results"]]
    assert origins == ["vector", "keyword"]


def test_threshold_does_not_drop_rrf_only_scores():
    groups = [{
        "results": [
            {"origin": "vector", "score": 0.03},
        ]
    }]
    apply_score_threshold(groups, 0.5)
    assert len(groups[0]["results"]) == 1


def test_threshold_keeps_top_vector_when_all_below():
    groups = [{
        "results": [
            {"origin": "vector", "vector_score": 0.30, "score": 0.30, "text": "best"},
            {"origin": "vector", "vector_score": 0.28, "score": 0.28, "text": "mid"},
            {"origin": "vector", "vector_score": 0.20, "score": 0.20, "text": "low"},
        ]
    }]
    apply_score_threshold(groups, 0.5)
    kept = groups[0]["results"]
    assert len(kept) == 3
    assert kept[0]["text"] == "best"
