"""In-memory exact cosine vector store (offline fallback / tests / small KB).

Author: 晨星
"""
from __future__ import annotations

from worldrag.embed.hash_embed import cosine
from worldrag.protocols import Chunk, SearchResult


class MemoryVectorStore:
    def __init__(self, dim: int) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self._dim = dim
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    @property
    def name(self) -> str:
        return "memory-cosine"

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks/vectors length mismatch")
        for v in vectors:
            if len(v) != self._dim:
                raise ValueError(f"vector dim mismatch: {len(v)} != {self._dim}")
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]:
        if len(query_vector) != self._dim:
            raise ValueError("query dim mismatch")
        scored = [
            SearchResult(chunk=c, score=cosine(query_vector, v), source="vector")
            for c, v in zip(self._chunks, self._vectors)
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[: max(k, 0)]

    def count(self) -> int:
        return len(self._chunks)

    def reset(self) -> None:
        self._chunks.clear()
        self._vectors.clear()
