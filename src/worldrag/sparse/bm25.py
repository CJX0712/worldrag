"""BM25 sparse index over the CJK-aware tokenizer.

ADR-004: the default engine is the built-in Robertson & Zaragoza (2009)
implementation with a strictly non-negative idf (ln(1 + (N-n+0.5)/(n+0.5))).
rank_bm25's BM25Okapi floors negative idf at ``epsilon * average_idf``,
which inverts ranking and yields all-negative scores on small corpora
(reproduced: scores [-0.366, -0.349] for a 2-doc index, correct doc last).
rank_bm25 is therefore NOT used by default; set WORLDRAG_BM25_ENGINE=rank_bm25
only for benchmarking on large corpora.

Author: 晨星
"""
from __future__ import annotations

import math
import os
from collections import Counter

from worldrag.protocols import Chunk, SearchResult
from worldrag.sparse.tokenizer import tokenize

try:
    from rank_bm25 import BM25Okapi as _LibBM25
except Exception:  # pragma: no cover
    _LibBM25 = None


class _MiniBM25:
    """Dependency-free BM25Okapi equivalent (Robertson & Zaragoza 2009)."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.doc_len = [len(d) for d in corpus]
        self.avgdl = sum(self.doc_len) / max(len(corpus), 1)
        self.tf = [Counter(d) for d in corpus]
        df: Counter[str] = Counter()
        for doc in corpus:
            df.update(set(doc))
        n = len(corpus)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def get_scores(self, query: list[str]) -> list[float]:
        scores = []
        for i, tf in enumerate(self.tf):
            denom_norm = self.k1 * (1 - self.b + self.b * self.doc_len[i] / max(self.avgdl, 1e-9))
            score = 0.0
            for term in query:
                f = tf.get(term, 0)
                if f:
                    score += self.idf.get(term, 0.0) * f * (self.k1 + 1) / (f + denom_norm)
            scores.append(score)
        return scores


class BM25Index:
    def __init__(self, engine: str | None = None) -> None:
        self._engine = engine or os.environ.get("WORLDRAG_BM25_ENGINE", "mini")
        self._chunks: list[Chunk] = []
        self._model = None  # built lazily on add

    @property
    def name(self) -> str:
        return f"bm25-{self._engine}"

    def add(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)
        corpus = [tokenize(c.text) for c in self._chunks]
        if not corpus:
            self._model = None
        elif self._engine == "rank_bm25" and _LibBM25 is not None:
            self._model = _LibBM25(corpus)
        else:
            self._model = _MiniBM25(corpus)

    def search(self, query: str, k: int) -> list[SearchResult]:
        if self._model is None or k <= 0:
            return []
        scores = self._model.get_scores(tokenize(query))
        ranked = sorted(zip(self._chunks, scores), key=lambda p: p[1], reverse=True)
        return [
            SearchResult(chunk=c, score=float(s), source="bm25")
            for c, s in ranked[:k]
            if s > 0
        ]
