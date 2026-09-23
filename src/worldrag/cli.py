"""WorldRAG CLI: ingest / query / evaluate / serve.

Author: 晨星
"""
from __future__ import annotations

import argparse
import json
import sys

from worldrag.config import Config
from worldrag.evaluate.runner import load_gold, run_evaluation
from worldrag.factory import build_pipeline
from worldrag.ingest.loaders import load_directory, load_file


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="worldrag", description="WorldRAG knowledge-base QA")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest a file or directory")
    p_ingest.add_argument("path")

    p_query = sub.add_parser("query", help="ask a question (after ingest in same session)")
    p_query.add_argument("query")
    p_query.add_argument("--corpus", help="corpus dir to ingest first")

    p_eval = sub.add_parser("evaluate", help="run offline evaluation")
    p_eval.add_argument("--corpus", default="data/samples")
    p_eval.add_argument("--gold", default="eval/gold.jsonl")

    p_serve = sub.add_parser("serve", help="run the API server")
    p_serve.add_argument("--port", type=int, default=None)

    args = parser.parse_args(argv)
    cfg = Config()

    if args.cmd == "ingest":
        pipeline, report = build_pipeline(cfg)
        from pathlib import Path

        path = Path(args.path)
        docs = load_directory(path) if path.is_dir() else [load_file(path)]
        n = pipeline.ingest_documents(docs)
        _print_json({"ingested_chunks": n, "degradations": report})
        return 0

    if args.cmd == "query":
        pipeline, report = build_pipeline(cfg)
        if args.corpus:
            pipeline.ingest_documents(load_directory(args.corpus))
        if pipeline.chunk_count == 0:
            print("error: knowledge base empty; pass --corpus or ingest first", file=sys.stderr)
            return 2
        answer = pipeline.query(args.query)
        _print_json({
            "answer": answer.answer,
            "citations": answer.citations,
            "backends": answer.backends,
            "degradations": report,
        })
        return 0

    if args.cmd == "evaluate":
        result = run_evaluation(load_directory(args.corpus), load_gold(args.gold), cfg)
        _print_json(result)
        return 0

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("worldrag.api.app:app", host="127.0.0.1",
                    port=args.port or cfg.api_port, log_level="info")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
