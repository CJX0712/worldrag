"""Core protocols and shared data types for WorldRAG.

Every external dependency (embedding model, vector database, LLM) is hidden
behind a Protocol. Production implementations are injected at assembly time;
zero-dependency offline implementations keep ``verify`` green with no network,
no API key and no model files.

Author: 晨星
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Chunk:
    """A retrievable text unit produced by the ingest pipeline."""

    doc_id: str
    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """One scored retrieval hit. ``source`` records which stage produced it."""

    chunk: Chunk
    score: float
    source: str  # "vector" | "bm25" | "fusion" | "rerank"


@dataclass
class Answer:
    """Final answer with traceable citations."""

    query: str
    answer: str
    citations: list[dict[str, Any]]
    contexts: list[SearchResult]
    backends: dict[str, str]


class Embedder(Protocol):
    """Maps text to dense vectors."""

    @property
    def dim(self) -> int: ...

    @property
    def name(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    """Dense ANN/exact retrieval over embedded chunks."""

    @property
    def name(self) -> str: ...

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, query_vector: list[float], k: int) -> list[SearchResult]: ...

    def count(self) -> int: ...

    def reset(self) -> None: ...


class SparseIndex(Protocol):
    """Lexical retrieval (BM25 family)."""

    @property
    def name(self) -> str: ...

    def add(self, chunks: list[Chunk]) -> None: ...

    def search(self, query: str, k: int) -> list[SearchResult]: ...


class Reranker(Protocol):
    """Re-scores fused candidates. May be a pass-through."""

    @property
    def name(self) -> str: ...

    def rerank(self, query: str, results: list[SearchResult], k: int) -> list[SearchResult]: ...


class LLM(Protocol):
    """Text generator used for answer synthesis."""

    @property
    def name(self) -> str: ...

    def generate(self, prompt: str, **kwargs: Any) -> str: ...
