"""Application assembly. Entry file: wiring only, zero business logic.

Author: 晨星
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from worldrag.api.routes import build_router
from worldrag.config import Config
from worldrag.factory import build_pipeline

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or Config()
    pipeline, report = build_pipeline(cfg)

    app = FastAPI(title="WorldRAG", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    app.state.pipeline = pipeline
    app.state.degradations = report
    app.include_router(build_router(pipeline, cfg), prefix="/api")

    @app.get("/api/degradations")
    def degradations() -> dict:
        return {"degradations": report}

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str) -> FileResponse:
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
