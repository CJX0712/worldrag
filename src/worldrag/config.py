"""Runtime configuration, resolved from environment variables.

Defaults are the fully-offline profile: hash embeddings + in-memory cosine
store + mock LLM. Production backends (Ollama / faiss / ONNX reranker) are
selected via env vars, so a clean machine can always reproduce the system
with zero model downloads.

Author: 晨星
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    value = os.environ.get(key, "").strip()
    return value if value else default


@dataclass(frozen=True)
class Config:
    # backend selection
    embed_backend: str = _env("WORLDRAG_EMBED_BACKEND", "hash")      # hash | ollama | fastembed
    vector_backend: str = _env("WORLDRAG_VECTOR_BACKEND", "memory")  # memory | faiss
    llm_backend: str = _env("WORLDRAG_LLM_BACKEND", "mock")          # mock | ollama
    rerank_backend: str = _env("WORLDRAG_RERANK_BACKEND", "none")    # none | onnx
    # ollama
    ollama_base_url: str = _env("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_embed_model: str = _env("WORLDRAG_OLLAMA_EMBED_MODEL", "bge-m3")
    ollama_llm_model: str = _env("WORLDRAG_OLLAMA_LLM_MODEL", "qwen2.5:1.5b-instruct")
    ollama_num_thread: int = int(_env("WORLDRAG_OLLAMA_NUM_THREAD", "4"))
    # embedding
    embed_dim: int = int(_env("WORLDRAG_EMBED_DIM", "384"))
    # chunking
    chunk_size: int = int(_env("WORLDRAG_CHUNK_SIZE", "500"))
    chunk_overlap: int = int(_env("WORLDRAG_CHUNK_OVERLAP", "60"))
    # retrieval
    vector_top_k: int = int(_env("WORLDRAG_VECTOR_TOP_K", "10"))
    bm25_top_k: int = int(_env("WORLDRAG_BM25_TOP_K", "10"))
    rrf_k: int = int(_env("WORLDRAG_RRF_K", "60"))
    rerank_candidates: int = int(_env("WORLDRAG_RERANK_CANDIDATES", "20"))
    final_top_k: int = int(_env("WORLDRAG_FINAL_TOP_K", "5"))
    # ADR-002: reranker score is blended into RRF order, never used alone
    rerank_weight: float = float(_env("WORLDRAG_RERANK_WEIGHT", "0.4"))
    rerank_model_dir: str = _env("WORLDRAG_RERANK_MODEL_DIR", "models/bge-reranker-v2-m3")
    # http
    request_timeout: float = float(_env("WORLDRAG_REQUEST_TIMEOUT", "120"))
    api_port: int = int(_env("WORLDRAG_API_PORT", "8000"))


DEFAULT_CONFIG = Config()
