"""BM25 sparse index: lexical relevance ranking for CJK text.

Author: 晨星
"""
from worldrag.protocols import Chunk
from worldrag.sparse.bm25 import BM25Index


def _chunk(doc_id: str, text: str) -> Chunk:
    return Chunk(doc_id=doc_id, chunk_id=f"{doc_id}#0000", text=text)


def test_relevant_doc_ranked_first():
    idx = BM25Index()
    idx.add([
        _chunk("refund", "年度套餐购买后十四天内享有无理由全额退款权利，审核需三个工作日。"),
        _chunk("deploy", "私有化部署最低要求八核CPU、三十二GB内存与五百GB存储。"),
        _chunk("security", "密码使用bcrypt加盐哈希存储，连续五次错误锁定账户。"),
    ])
    hits = idx.search("退款需要多少天", k=3)
    assert hits[0].chunk.doc_id == "refund"


def test_number_exact_match():
    idx = BM25Index()
    idx.add([
        _chunk("a", "免费版每分钟六十次请求，每日一万次。"),
        _chunk("b", "专业版每分钟六百次请求。"),
    ])
    hits = idx.search("429 状态码", k=2)
    assert hits == []  # neither doc mentions 429 -> no fabricated hits
    hits = idx.search("六十次", k=2)
    assert hits[0].chunk.doc_id == "a"


def test_empty_index_and_zero_k():
    idx = BM25Index()
    assert idx.search("任意", k=5) == []
    idx.add([_chunk("a", "内容")])
    assert idx.search("内容", k=0) == []


def test_zero_score_results_excluded():
    idx = BM25Index()
    idx.add([_chunk("a", "苹果香蕉橘子")])
    hits = idx.search("xyzabc 不存在", k=5)  # zero token overlap with the doc
    assert hits == []
