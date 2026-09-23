"""End-to-end offline pipeline: ingest (multi-chunk) -> query -> citations.

Author: 晨星
"""
import pytest

from worldrag.agent.pipeline import RAGPipeline
from worldrag.config import Config
from worldrag.embed.hash_embed import HashEmbedder
from worldrag.ingest.loaders import RawDocument
from worldrag.llm.mock import MockLLM
from worldrag.rerank.base import PassThroughReranker
from worldrag.sparse.bm25 import BM25Index
from worldrag.vector.memory import MemoryVectorStore

# each doc > 500 chars so the default chunker MUST produce >1 chunk per doc
DOC_A = RawDocument(
    doc_id="refund",
    text=("年度套餐购买后十四天内享有无理由全额退款权利。退款申请通过控制台账单页面提交，"
          "系统在三个工作日内完成审核，款项在七个工作日内原路退回。") * 10,
)
DOC_B = RawDocument(
    doc_id="deploy",
    text=("私有化部署最低要求八核CPU、三十二GB内存、五百GB SSD存储。健康检查端点为healthz，"
          "负载均衡器每十秒探测一次，连续三次失败判定节点下线。") * 10,
)


@pytest.fixture()
def pipeline() -> RAGPipeline:
    cfg = Config()
    pipe = RAGPipeline(
        embedder=HashEmbedder(cfg.embed_dim),
        vector_store=MemoryVectorStore(cfg.embed_dim),
        sparse_index=BM25Index(),
        reranker=PassThroughReranker(),
        llm=MockLLM(),
        config=cfg,
    )
    return pipe


def test_ingest_produces_multiple_chunks(pipeline):
    n = pipeline.ingest_documents([DOC_A, DOC_B])
    assert n > 2  # multi-chunk path genuinely covered
    assert pipeline.chunk_count == n


def test_query_returns_relevant_context_and_citation(pipeline):
    pipeline.ingest_documents([DOC_A, DOC_B])
    answer = pipeline.query("退款审核需要几个工作日？")
    assert answer.answer
    assert answer.contexts, "must retrieve contexts"
    top_doc_ids = {r.chunk.doc_id for r in answer.contexts[:2]}
    assert "refund" in top_doc_ids
    assert answer.citations[0]["doc_id"] in top_doc_ids
    assert "snippet" in answer.citations[0]


def test_query_cross_doc_discrimination(pipeline):
    pipeline.ingest_documents([DOC_A, DOC_B])
    answer = pipeline.query("私有化部署的最低内存要求是多少？")
    assert answer.contexts[0].chunk.doc_id == "deploy"


def test_empty_query_rejected(pipeline):
    pipeline.ingest_documents([DOC_A])
    with pytest.raises(ValueError):
        pipeline.query("   ")


def test_backends_reported(pipeline):
    names = pipeline.backends()
    assert names["embed"].startswith("hash-bigram")
    assert names["vector"] == "memory-cosine"
    assert names["llm"] == "mock-extractive"
