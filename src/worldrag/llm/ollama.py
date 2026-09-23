"""Ollama-backed chat LLM (production default).

CPU inference note: on CPU the bottleneck is memory bandwidth, not compute.
Ollama defaults to cpu_count-1 threads which is ~4x slower for small
quantised models; we pin num_thread to 4 (configurable, 2-4 is the sweet
spot on typical laptop CPUs).

Author: 晨星
"""
from __future__ import annotations

import httpx


class OllamaLLM:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 120.0,
        num_thread: int = 4,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._num_thread = num_thread
        # trust_env=False: a local Ollama must never be reached through a
        # system/SOCKS proxy (proxy env vars cause WinError 10054 resets)
        self._client = httpx.Client(timeout=timeout, trust_env=False)

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    def generate(self, prompt: str, **kwargs: object) -> str:
        resp = self._client.post(
            f"{self._base}/api/chat",
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "num_thread": int(kwargs.get("num_thread", self._num_thread)),
                    "temperature": float(kwargs.get("temperature", 0.2)),
                    "num_ctx": int(kwargs.get("num_ctx", 4096)),
                },
            },
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        if not content.strip():
            raise RuntimeError("ollama returned empty completion")
        return content

    def close(self) -> None:
        self._client.close()
