"""faiss-cpu backed vector store (production default when available).

Vectors are L2-normalised and indexed with IndexFlatIP, so inner product ==
cosine similarity. ``_error`` is exposed so callers can assert the real
backend is actually live instead of silently degraded (hard lesson learned:
a silent fallback keeps every test green while production is broken).

Author: 晨星
"""
from __future__ import annotations

from worldrag.protocols import Chunk, SearchResult


class FaissVectorStore:
    def __init__(self, dim: int) -> None:
        self._error: Exception | None = None
        try:
            import faiss
            import numpy as np
        except Exception as exc:  # pragma: no cover
            self._error = exc
            raise RuntimeError(f"faiss backend unavailable: {exc}") from exc
        self._np = np
        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)
        self._chunks: list[Chunk] = []

    @property
    def name(self) -> str:
        return "faiss-IndexFlatIP"

    def _normalize(self, mat: "object") -> "object":
        np = self._np
        arr = np.asarray(mat, dtype="float32")
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return arr / norms

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks/vectors length mismatch")
        if not chunks:
            return
        self._index.add(self._normalize(vectors))
        self._chunks.extend(chunks)

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        if self._index.ntotal == 0 or k <= 0:
            return []
        q = self._normalize([query_vector])
        k = min(k, self._index.ntotal)
        scores, ids = self._index.search(q, k)
        return [
            SearchResult(chunk=self._chunks[i], score=float(s), source="vector")
            for s, i in zip(scores[0], ids[0])
            if 0 <= i < len(self._chunks)
        ]

    def count(self) -> int:
        return int(self._index.ntotal)

    def reset(self) -> None:
        self._index.reset()
        self._chunks.clear()
