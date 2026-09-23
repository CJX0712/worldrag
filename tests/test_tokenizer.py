"""CJK tokenizer: unigram+bigram coverage, latin passthrough.

Author: 晨星
"""
from worldrag.sparse.tokenizer import tokenize


def test_cjk_unigrams_and_bigrams():
    tokens = tokenize("退款政策")
    for ch in "退款政策":
        assert ch in tokens
    assert "退款" in tokens
    assert "款政" in tokens
    assert "政策" in tokens


def test_latin_words_extracted():
    tokens = tokenize("API 返回 HTTP 429")
    assert "api" in tokens
    assert "http" in tokens
    assert "429" in tokens


def test_mixed_text_and_empty():
    assert tokenize("") == []
    tokens = tokenize("bcrypt 加密算法")
    assert "bcrypt" in tokens
    assert "加密" in tokens


def test_bigrams_do_not_cross_punctuation():
    # "政策。安全" must NOT yield the cross-boundary bigram "策安"
    tokens = tokenize("政策。安全")
    assert "策安" not in tokens
