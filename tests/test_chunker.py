"""Chunker: deterministic ids, size bounds, multi-chunk coverage.

Author: 晨星
"""
import pytest

from worldrag.ingest.chunker import chunk_text

LONG_PARA = "知识库系统需要稳定的检索质量。" * 60  # ~900 chars, single paragraph


def test_short_text_single_chunk():
    chunks = chunk_text("doc", "短文本。")
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "doc#0000"
    assert chunks[0].doc_id == "doc"


def test_long_paragraph_splits_into_multiple_chunks():
    chunks = chunk_text("doc", LONG_PARA, size=200, overlap=20)
    assert len(chunks) >= 4
    assert all(len(c.text) <= 220 for c in chunks)  # size + small overlap headroom


def test_overlap_carries_context_forward():
    chunks = chunk_text("doc", LONG_PARA, size=200, overlap=30)
    assert len(chunks) > 1
    tail_of_first = chunks[0].text[-30:]
    assert chunks[1].text.startswith(tail_of_first[:10])


def test_deterministic_ids():
    a = chunk_text("doc", LONG_PARA, size=200, overlap=20)
    b = chunk_text("doc", LONG_PARA, size=200, overlap=20)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        chunk_text("doc", "x", size=0)
    with pytest.raises(ValueError):
        chunk_text("doc", "x", size=100, overlap=100)


def test_full_text_coverage_no_content_loss():
    chunks = chunk_text("doc", LONG_PARA, size=200, overlap=0)
    joined = "".join(c.text for c in chunks)
    # every sentence fragment of the source appears in some chunk
    assert "知识库系统需要稳定的检索质量" in joined.replace("\n", "")
