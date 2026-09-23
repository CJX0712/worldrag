"""RRF fusion + blending math (ADR-002).

Author: 晨星
"""
import pytest

from worldrag.protocols import Chunk, SearchResult
from worldrag.rerank.fusion import blend_scores, min_max_normalize, rrf_fuse


def _hit(cid: str, score: float, source: str) -> SearchResult:
    return SearchResult(chunk=Chunk(doc_id=cid, chunk_id=cid, text=cid), score=score, source=source)


def test_rrf_prefers_item_ranked_high_in_both_lists():
    vec = [_hit("a", 0.9, "vector"), _hit("b", 0.8, "vector"), _hit("c", 0.7, "vector")]
    bm = [_hit("b", 12.0, "bm25"), _hit("x", 11.0, "bm25"), _hit("a", 10.0, "bm25")]
    fused = rrf_fuse([vec, bm], rrf_k=60)
    ids = [r.chunk.chunk_id for r in fused]
    # b: ranks 1 and 0 -> 1/62 + 1/61; a: ranks 0 and 2 -> 1/61 + 1/64; b wins
    assert ids[0] == "b"
    assert ids[1] == "a"
    assert set(ids) == {"a", "b", "c", "x"}


def test_rrf_scores_are_reciprocal_rank():
    fused = rrf_fuse([[_hit("x", 1.0, "vector")]], rrf_k=60)
    assert fused[0].score == pytest.approx(1.0 / 61.0)


def test_min_max_normalize_degenerate_inputs():
    assert min_max_normalize([]) == []
    assert min_max_normalize([3.0, 3.0]) == [1.0, 1.0]
    assert min_max_normalize([0.0, 5.0, 10.0]) == [0.0, 0.5, 1.0]


def test_blend_weight_bounds_and_direction():
    base = [10.0, 1.0]     # item0 wins on RRF
    signal = [0.1, 0.9]    # item1 wins on CE
    assert blend_scores(base, signal, 0.0) == [1.0, 0.0]  # pure RRF order
    assert blend_scores(base, signal, 1.0) == [0.0, 1.0]  # pure CE order
    blended = blend_scores(base, signal, 0.4)
    assert blended[0] > blended[1]  # bounded weight: RRF still dominates


def test_blend_length_mismatch_rejected():
    with pytest.raises(ValueError):
        blend_scores([1.0], [1.0, 2.0], 0.5)
