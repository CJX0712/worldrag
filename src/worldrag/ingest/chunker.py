"""Deterministic paragraph-aware text chunker with overlap.

Paragraph-first splitting keeps CJK sentences intact; chunk ids are stable
(``{doc_id}#{seq:04d}``) so re-ingesting the same corpus is idempotent.

Author: 晨星
"""
from __future__ import annotations

import re

from worldrag.protocols import Chunk

_PARA_SPLIT = re.compile(r"\n\s*\n")


def _hard_split(text: str, size: int, overlap: int) -> list[str]:
    """Split an over-long paragraph on sentence boundaries, then by length."""
    sentences = re.split(r"(?<=[。！？!?；;\.])\s*", text)
    pieces: list[str] = []
    buf = ""
    for sent in sentences:
        if not sent:
            continue
        if len(buf) + len(sent) <= size:
            buf += sent
            continue
        if buf:
            pieces.append(buf)
        if len(sent) > size:  # single sentence still too long: cut by length
            step = max(size - overlap, 1)
            pieces.extend(sent[i : i + size] for i in range(0, len(sent), step))
            buf = ""
        else:
            buf = sent
    if buf:
        pieces.append(buf)
    return pieces


def chunk_text(
    doc_id: str,
    text: str,
    size: int = 500,
    overlap: int = 60,
    metadata: dict | None = None,
) -> list[Chunk]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")

    paragraphs = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    windows: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > size:
            if buf:
                windows.append(buf)
                buf = ""
            windows.extend(_hard_split(para, size, overlap))
        elif len(buf) + len(para) + 1 <= size:
            buf = f"{buf}\n{para}" if buf else para
        else:
            windows.append(buf)
            buf = para
    if buf:
        windows.append(buf)

    if overlap and len(windows) > 1:
        windows = _apply_overlap(windows, overlap)

    meta = dict(metadata or {})
    return [
        Chunk(doc_id=doc_id, chunk_id=f"{doc_id}#{i:04d}", text=w, metadata=meta)
        for i, w in enumerate(windows)
        if w.strip()
    ]


def _apply_overlap(windows: list[str], overlap: int) -> list[str]:
    """Prefix each window (except the first) with the tail of the previous one."""
    out = [windows[0]]
    for prev, cur in zip(windows, windows[1:]):
        tail = prev[-overlap:]
        out.append(f"{tail}\n{cur}" if tail else cur)
    return out
