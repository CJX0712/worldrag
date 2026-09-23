"""Reciprocal Rank Fusion (RRF) + score blending utilities.

RRF (Cormack et al. 2009) merges ranked lists without score calibration -
critical because BM25 scores and cosine similarities live on incomparable
scales.

ADR-002: a cross-encoder rerank score is NEVER used as the final order on
its own. It is min-max normalised and blended into the normalised RRF score
with a bounded weight (default 0.4). This prevents a reranker that is weak
in the query language from silently burying the correct answer.

Author: 晨星
"""
from __future__ import annotations

from worldrag.protocols import SearchResult


def rrf_fuse(
    result_lists: list[list[SearchResult]],
    rrf_k: int = 60,
    top: int | None = None,
) -> list[SearchResult]:
    """Fuse multiple ranked lists. rank positions are 0-based."""
    scores: dict[str, float] = {}
    best: dict[str, SearchResult] = {}
    for results in result_lists:
        for rank, r in enumerate(results):
            cid = r.chunk.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
            if cid not in best or r.score > best[cid].score:
                best[cid] = r
    fused = [
        SearchResult(chunk=best[cid].chunk, score=score, source="fusion")
        for cid, score in scores.items()
    ]
    fused.sort(key=lambda r: r.score, reverse=True)
    return fused[:top] if top else fused


def min_max_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [1.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def blend_scores(
    base: list[float],
    signal: list[float],
    weight: float,
) -> list[float]:
    """final = (1-w) * norm(base) + w * norm(signal). w is clamped to [0, 1]."""
    if len(base) != len(signal):
        raise ValueError("base/signal length mismatch")
    w = min(max(weight, 0.0), 1.0)
    nb, ns = min_max_normalize(base), min_max_normalize(signal)
    return [(1 - w) * b + w * s for b, s in zip(nb, ns)]
