"""Document loaders: .txt / .md / .pdf -> raw documents.

Author: 晨星
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


@dataclass
class RawDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required for PDF ingest: pip install pypdf") from exc
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(p for p in pages if p)


def load_file(path: str | Path) -> RawDocument:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"document not found: {p}")
    suffix = p.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported file type: {suffix} (supported: {sorted(SUPPORTED_SUFFIXES)})")
    text = load_pdf(p) if suffix == ".pdf" else load_text(p)
    if not text.strip():
        raise ValueError(f"empty document: {p}")
    return RawDocument(doc_id=p.stem, text=text, metadata={"source": str(p), "type": suffix})


def load_directory(path: str | Path) -> list[RawDocument]:
    p = Path(path)
    if not p.is_dir():
        raise NotADirectoryError(f"not a directory: {p}")
    docs = [load_file(f) for f in sorted(p.rglob("*")) if f.suffix.lower() in SUPPORTED_SUFFIXES]
    if not docs:
        raise ValueError(f"no supported documents under: {p}")
    return docs
