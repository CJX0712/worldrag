"""Hash embedder invariants: dim, normalisation, determinism, separability.

Author: 晨星
"""
import math

from worldrag.embed.hash_embed import HashEmbedder, cosine


def test_dim_and_normalisation():
    emb = HashEmbedder(128)
    vec = emb.embed(["退款政策规定十四天内可全额退款"])[0]
    assert len(vec) == 128
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-9


def test_determinism():
    emb = HashEmbedder(64)
    assert emb.embed(["同一段文本"]) == emb.embed(["同一段文本"])


def test_identical_texts_have_cosine_one():
    emb = HashEmbedder(256)
    a = emb.embed(["私有化部署需要八核CPU"])[0]
    b = emb.embed(["私有化部署需要八核CPU"])[0]
    assert abs(cosine(a, b) - 1.0) < 1e-9


def test_similar_texts_closer_than_dissimilar():
    emb = HashEmbedder(384)
    q = emb.embed(["退款政策与申请流程"])[0]
    near = emb.embed(["退款申请流程与政策说明"])[0]
    far = emb.embed(["数据库主从架构与负载均衡配置"])[0]
    assert cosine(q, near) > cosine(q, far)


def test_empty_text_does_not_crash():
    emb = HashEmbedder(32)
    vec = emb.embed([""])[0]
    assert len(vec) == 32
