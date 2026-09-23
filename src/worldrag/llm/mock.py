"""Deterministic offline LLM (mock-extractive).

Extracts the leading sentences of the top-ranked context from the prompt
built by the agent pipeline, so the full retrieve -> generate -> cite chain
is verifiable with no model, no network and no API key (ADR-003).

Author: 晨星
"""
from __future__ import annotations

import re

_CONTEXT_RE = re.compile(r"资料\s*(\d+)[：:](.*?)(?=\n资料\s*\d+[：:]|\Z)", re.S)


class MockLLM:
    def __init__(self, max_sentences: int = 3) -> None:
        self._max_sentences = max_sentences

    @property
    def name(self) -> str:
        return "mock-extractive"

    def generate(self, prompt: str, **kwargs: object) -> str:
        contexts = _CONTEXT_RE.findall(prompt)
        if not contexts:
            return "（离线模式）未检索到可用资料，无法回答。"
        n, body = contexts[0]
        sentences = [s.strip() for s in re.split(r"(?<=[。！？!?；;])", body) if s.strip()]
        picked = "".join(sentences[: self._max_sentences]) or body.strip()[:200]
        return f"（离线模式·基于检索资料）{picked}[{n}]"
