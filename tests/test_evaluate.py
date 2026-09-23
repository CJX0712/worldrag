"""Evaluation discipline: fresh-index isolation + metric correctness.

The anti-regression invariant: polluting a production-like index must NOT
change evaluation metrics, because the evaluator always builds a fresh
pipeline on fresh indexes.

Author: 晨星
"""
from worldrag.config import Config
from worldrag.evaluate.runner import run_evaluation
from worldrag.ingest.loaders import RawDocument

CORPUS = [
    RawDocument(doc_id="alpha", text=("苹果是一种常见的水果，富含维生素。" * 40)),
    RawDocument(doc_id="beta", text=("量子计算利用叠加态进行并行计算。" * 40)),
]
GOLD = [
    {"query": "苹果富含什么？", "relevant_doc_ids": ["alpha"], "expected_keywords": ["维生素"]},
    {"query": "量子计算利用什么态？", "relevant_doc_ids": ["beta"], "expected_keywords": ["叠加"]},
]


def test_evaluation_metrics_on_clean_corpus():
    result = run_evaluation(CORPUS, GOLD, Config())
    m = result["metrics"]
    assert m["queries"] == 2
    assert m["chunks"] > 2  # multi-chunk ingest covered
    assert m["recall_at_k"] == 1.0
    assert m["mrr"] == 1.0
    assert m["keyword_hit_rate"] == 1.0


def test_evaluation_isolated_from_external_index_pollution():
    baseline = run_evaluation(CORPUS, GOLD, Config())["metrics"]

    # pollute a DIFFERENT (production-like) pipeline's index with noise
    from worldrag.factory import build_pipeline

    noisy, _ = build_pipeline(Config())
    noisy.ingest_documents([
        RawDocument(doc_id="noise", text=("苹果是手机品牌发布会的热门话题。" * 40))
    ])

    after = run_evaluation(CORPUS, GOLD, Config())["metrics"]
    assert after == baseline  # metrics bit-for-bit unchanged


def test_evaluation_reports_backends_and_no_silent_degradation():
    result = run_evaluation(CORPUS, GOLD, Config())
    assert result["backends"]["vector"] == "memory-cosine"
    assert result["degradations"] == {}
    for row in result["per_query"]:
        assert row["hit"] is True
        assert row["rank"] == 1
