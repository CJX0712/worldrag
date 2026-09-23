"""Evaluation runner: recall@k / MRR / keyword hit-rate.

Hard rules (learned from production incidents):
1. Evaluation ALWAYS builds a brand-new pipeline on fresh in-memory indexes.
   It never reads from, nor writes to, any production index.
2. Corpus is re-ingested on every run - no "only ingest when empty" shortcuts.
3. Results are reported with the active backend names so a silent degradation
   is visible in the metrics payload itself.

Author: 晨星
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from worldrag.config import Config
from worldrag.factory import build_pipeline
from worldrag.ingest.loaders import RawDocument, load_directory


def load_gold(path: str | Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    if not items:
        raise ValueError(f"gold file is empty: {path}")
    return items


def run_evaluation(
    corpus: list[RawDocument],
    gold: list[dict[str, Any]],
    cfg: Config,
) -> dict[str, Any]:
    pipeline, report = build_pipeline(cfg)  # fresh pipeline, fresh indexes
    ingested = pipeline.ingest_documents(corpus)
    if ingested == 0:
        raise RuntimeError("evaluation corpus produced zero chunks")

    per_query: list[dict[str, Any]] = []
    hits = 0
    rr_sum = 0.0
    kw_hits = 0
    for item in gold:
        answer = pipeline.query(item["query"])
        retrieved_doc_ids = [r.chunk.doc_id for r in answer.contexts]
        relevant = set(item["relevant_doc_ids"])

        rank = next(
            (i + 1 for i, d in enumerate(retrieved_doc_ids) if d in relevant), None
        )
        hit = rank is not None
        hits += int(hit)
        rr_sum += 1.0 / rank if rank else 0.0

        expected_kw = item.get("expected_keywords", [])
        haystack = answer.answer + " " + " ".join(r.chunk.text for r in answer.contexts)
        kw_hit = all(kw in haystack for kw in expected_kw)
        kw_hits += int(kw_hit)

        per_query.append({
            "query": item["query"],
            "hit": hit,
            "rank": rank,
            "keyword_hit": kw_hit,
            "retrieved": retrieved_doc_ids,
        })

    n = len(gold)
    return {
        "metrics": {
            "recall_at_k": round(hits / n, 4),
            "mrr": round(rr_sum / n, 4),
            "keyword_hit_rate": round(kw_hits / n, 4),
            "queries": n,
            "chunks": ingested,
        },
        "backends": pipeline.backends(),
        "degradations": report,
        "per_query": per_query,
    }


def run_from_disk(corpus_dir: str | Path, gold_path: str | Path, cfg: Config) -> dict[str, Any]:
    return run_evaluation(load_directory(corpus_dir), load_gold(gold_path), cfg)
