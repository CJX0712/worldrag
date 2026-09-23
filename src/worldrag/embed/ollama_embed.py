"""Ollama-backed embedder (production default, e.g. bge-m3).

Uses the local Ollama HTTP API - no model download, no HF dependency.
``dim`` is probed lazily on first use and cached.

Author: 晨星
"""
from __future__ import annotations

import httpx


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._dim: int | None = None
        # trust_env=False: never route localhost traffic through a proxy
        self._client = httpx.Client(timeout=timeout, trust_env=False)

    @property
    def name(self) -> str:
        return f"ollama-embed:{self._model}"

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed(["dimension probe"])[0])
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.post(
            f"{self._base}/api/embed",
            json={"model": self._model, "input": texts},
        )
        resp.raise_for_status()
        embeddings = resp.json()["embeddings"]
        if len(embeddings) != len(texts):
            raise RuntimeError(f"ollama embed count mismatch: {len(embeddings)} != {len(texts)}")
        return embeddings

    def close(self) -> None:
        self._client.close()
