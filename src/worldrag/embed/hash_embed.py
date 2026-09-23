"""Zero-dependency hashing embedder (offline fallback / CI).

Word + character-bigram hashing works for CJK text where whitespace
tokenisation fails. Deterministic and L2-normalised. It is NOT semantically
strong - it exists so the entire pipeline is verifiable with no model
download (ADR-003). Production uses OllamaEmbedder.

Author: 晨星
"""
from __future__ import annotations

import hashlib
import math

_CJK_LO, _CJK_HI = "一", "鿿"  # CJK Unified Ideographs


class HashEmbedder:
    def __init__(self, dim: int = 384) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"hash-bigram-{self._dim}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for feat in self._features(text.lower()):
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:8], "little")
            vec[bucket % self._dim] += 1.0
        return _l2_normalize(vec)

    @staticmethod
    def _features(text: str) -> list[str]:
        words = text.split()
        feats = [f"w:{w}" for w in words]
        compact = "".join(words)
        feats.extend(f"b:{compact[i:i + 2]}" for i in range(len(compact) - 1))
        feats.extend(f"c:{ch}" for ch in compact if _CJK_LO <= ch <= _CJK_HI)
        return feats or ["<empty>"]


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity for L2-normalised vectors (plain dot product)."""
    return sum(x * y for x, y in zip(a, b))
