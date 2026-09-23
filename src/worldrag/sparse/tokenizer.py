"""Zero-dependency CJK-aware tokenizer for BM25.

Contiguous CJK runs contribute unigrams + bigrams (bigrams carry most of the
discriminative signal for Chinese); latin/digit runs contribute whole words.
Replaces jieba, which has no Windows wheel and cannot be a hard dependency.

Author: 晨星
"""
from __future__ import annotations

import re

_CJK_RUN = re.compile(r"[一-鿿]+")
_LATIN_RUN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens: list[str] = []
    for run in _CJK_RUN.findall(lowered):
        tokens.extend(run)  # unigrams
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))  # bigrams
    tokens.extend(_LATIN_RUN.findall(lowered))
    return tokens
