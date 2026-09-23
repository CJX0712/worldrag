"""Backend factory: assembles a RAGPipeline from Config.

Assembly-only module - zero business logic. Any unavailable production
backend degrades to its offline counterpart and the degradation is recorded
in ``report`` so it can never happen silently (anti fake-green rule).

Author: 晨星
"""
from __future__ import annotations

from worldrag.agent.pipeline import RAGPipeline
from worldrag.config import Config
from worldrag.embed.hash_embed import HashEmbedder
from worldrag.llm.mock import MockLLM
from worldrag.rerank.base import PassThroughReranker
from worldrag.sparse.bm25 import BM25Index
from worldrag.vector.memory import MemoryVectorStore


def build_pipeline(cfg: Config) -> tuple[RAGPipeline, dict[str, str]]:
    report: dict[str, str] = {}

    # ---- embedder ----
    embedder = HashEmbedder(cfg.embed_dim)
    if cfg.embed_backend == "ollama":
        try:
            from worldrag.embed.ollama_embed import OllamaEmbedder

            candidate = OllamaEmbedder(cfg.ollama_base_url, cfg.ollama_embed_model, cfg.request_timeout)
            _ = candidate.dim  # probe: raises if Ollama is down
            embedder = candidate
        except Exception as exc:
            report["embed_degraded"] = f"{type(exc).__name__}: {exc}"
    elif cfg.embed_backend == "fastembed":
        try:
            from fastembed import TextEmbedding

            embedder = _FastembedAdapter(TextEmbedding())
        except Exception as exc:
            report["embed_degraded"] = f"{type(exc).__name__}: {exc}"

    # ---- vector store ----
    try:
        dim = embedder.dim
    except Exception:
        dim = cfg.embed_dim
    store = MemoryVectorStore(dim)
    if cfg.vector_backend == "faiss":
        try:
            from worldrag.vector.faiss_impl import FaissVectorStore

            store = FaissVectorStore(dim)
            assert store._error is None
        except Exception as exc:
            report["vector_degraded"] = f"{type(exc).__name__}: {exc}"

    # ---- reranker ----
    reranker = PassThroughReranker()
    if cfg.rerank_backend == "onnx":
        try:
            from worldrag.rerank.base import OnnxReranker

            reranker = OnnxReranker(cfg.rerank_model_dir, weight=cfg.rerank_weight)
            assert reranker._error is None
        except Exception as exc:
            report["rerank_degraded"] = f"{type(exc).__name__}: {exc}"

    # ---- llm ----
    llm = MockLLM()
    if cfg.llm_backend == "ollama":
        try:
            from worldrag.llm.ollama import OllamaLLM

            candidate = OllamaLLM(
                cfg.ollama_base_url, cfg.ollama_llm_model,
                timeout=cfg.request_timeout, num_thread=cfg.ollama_num_thread,
            )
            llm = candidate
        except Exception as exc:
            report["llm_degraded"] = f"{type(exc).__name__}: {exc}"

    pipeline = RAGPipeline(
        embedder=embedder, vector_store=store, sparse_index=BM25Index(),
        reranker=reranker, llm=llm, config=cfg,
    )
    return pipeline, report


class _FastembedAdapter:
    """Adapts fastembed.TextEmbedding to the Embedder protocol."""

    def __init__(self, model: "object") -> None:
        self._model = model
        self._dim: int | None = None

    @property
    def name(self) -> str:
        return "fastembed-onnx"

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed(["dimension probe"])[0])
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(texts)]
