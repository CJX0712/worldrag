"""Agent orchestration pipeline: retrieve -> fuse -> rerank -> generate -> cite.

Single entry point for both the API layer and the evaluator. Holds no state
beyond references to injected backends - all storage lives behind the
VectorStore / SparseIndex protocols.

Author: 晨星
"""
from __future__ import annotations

from worldrag.config import Config
from worldrag.ingest.chunker import chunk_text
from worldrag.ingest.loaders import RawDocument
from worldrag.protocols import (
    Answer,
    Chunk,
    Embedder,
    LLM,
    Reranker,
    SearchResult,
    SparseIndex,
    VectorStore,
)
from worldrag.rerank.fusion import rrf_fuse

_PROMPT_TEMPLATE = """你是一个严谨的知识库问答助手。仅根据下面给出的资料回答问题，
不得编造资料中没有的信息；回答中引用资料时用 [编号] 标注来源。
如果资料不足以回答，请明确说明。

{contexts}

问题：{query}
回答："""


class RAGPipeline:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        sparse_index: SparseIndex,
        reranker: Reranker,
        llm: LLM,
        config: Config,
    ) -> None:
        self._embedder = embedder
        self._vector = vector_store
        self._sparse = sparse_index
        self._reranker = reranker
        self._llm = llm
        self._cfg = config

    # ---------------- ingest ----------------

    def ingest_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vectors = self._embedder.embed([c.text for c in chunks])
        self._vector.add(chunks, vectors)
        self._sparse.add(chunks)
        return len(chunks)

    def ingest_documents(self, docs: list[RawDocument]) -> int:
        total = 0
        for doc in docs:
            chunks = chunk_text(
                doc.doc_id, doc.text,
                size=self._cfg.chunk_size, overlap=self._cfg.chunk_overlap,
                metadata=doc.metadata,
            )
            total += self.ingest_chunks(chunks)
        return total

    @property
    def chunk_count(self) -> int:
        return self._vector.count()

    def backends(self) -> dict[str, str]:
        return {
            "embed": self._embedder.name,
            "vector": self._vector.name,
            "sparse": self._sparse.name,
            "rerank": self._reranker.name,
            "llm": self._llm.name,
        }

    # ---------------- query ----------------

    def retrieve(self, query: str) -> list[SearchResult]:
        qv = self._embedder.embed([query])[0]
        vec_hits = self._vector.search(qv, self._cfg.vector_top_k)
        bm_hits = self._sparse.search(query, self._cfg.bm25_top_k)
        fused = rrf_fuse([vec_hits, bm_hits], rrf_k=self._cfg.rrf_k, top=self._cfg.rerank_candidates)
        return self._reranker.rerank(query, fused, self._cfg.final_top_k)

    def query(self, query: str) -> Answer:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        contexts = self.retrieve(query)
        prompt = self._compose_prompt(query, contexts)
        text = self._llm.generate(prompt)
        citations = [
            {
                "n": i + 1,
                "doc_id": r.chunk.doc_id,
                "chunk_id": r.chunk.chunk_id,
                "score": round(r.score, 6),
                "source": r.source,
                "snippet": r.chunk.text[:120],
            }
            for i, r in enumerate(contexts)
        ]
        return Answer(
            query=query, answer=text, citations=citations,
            contexts=contexts, backends=self.backends(),
        )

    @staticmethod
    def _compose_prompt(query: str, contexts: list[SearchResult]) -> str:
        if contexts:
            body = "\n".join(f"资料 {i + 1}：{r.chunk.text}" for i, r in enumerate(contexts))
        else:
            body = "（无检索结果）"
        return _PROMPT_TEMPLATE.format(contexts=body, query=query)
