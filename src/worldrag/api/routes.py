"""HTTP routes. Depends only on the RAGPipeline abstraction, never on
concrete backends - the pipeline is injected by app.py at assembly time.

Author: 晨星
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from worldrag.agent.pipeline import RAGPipeline
from worldrag.config import Config
from worldrag.ingest.loaders import RawDocument, load_file


class IngestTextItem(BaseModel):
    text: str = Field(min_length=1)
    doc_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    texts: list[IngestTextItem] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)


def _answer_payload(answer) -> dict[str, Any]:
    return {
        "query": answer.query,
        "answer": answer.answer,
        "citations": answer.citations,
        "backends": answer.backends,
    }


def build_router(pipeline: RAGPipeline, cfg: Config) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "chunks": pipeline.chunk_count, "backends": pipeline.backends()}

    @router.post("/ingest")
    def ingest(req: IngestRequest) -> dict[str, Any]:
        if not req.texts and not req.paths:
            raise HTTPException(status_code=400, detail="texts or paths required")
        docs: list[RawDocument] = []
        for i, item in enumerate(req.texts):
            docs.append(RawDocument(
                doc_id=item.doc_id or f"inline-{i:04d}",
                text=item.text, metadata=item.metadata,
            ))
        for p in req.paths:
            try:
                docs.append(load_file(Path(p)))
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            n = pipeline.ingest_documents(docs)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"ingest failed: {exc}") from exc
        return {"ingested_chunks": n, "total_chunks": pipeline.chunk_count}

    @router.post("/query")
    def query(req: QueryRequest) -> dict[str, Any]:
        if pipeline.chunk_count == 0:
            raise HTTPException(status_code=409, detail="knowledge base is empty; ingest first")
        try:
            return _answer_payload(pipeline.query(req.query))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"generation failed: {exc}") from exc

    @router.post("/evaluate")
    def evaluate() -> dict[str, Any]:
        from worldrag.evaluate.runner import load_gold, run_evaluation
        from worldrag.ingest.loaders import load_directory

        root = Path(__file__).resolve().parents[3]
        corpus = load_directory(root / "data" / "samples")
        gold = load_gold(root / "eval" / "gold.jsonl")
        return run_evaluation(corpus, gold, cfg)  # fresh pipeline inside

    return router
