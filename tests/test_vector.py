"""Vector stores: memory (always) and faiss (when installed).

Faiss test asserts _error is None so a broken real backend can never pass
silently by degrading to the in-memory path.

Author: 晨星
"""
import pytest

from worldrag.protocols import Chunk
from worldrag.vector.memory import MemoryVectorStore


def _chunks(n: int) -> list[Chunk]:
    return [Chunk(doc_id=f"d{i}", chunk_id=f"d{i}#0000", text=f"text {i}") for i in range(n)]


def _one_hot(dim: int, i: int) -> list[float]:
    v = [0.0] * dim
    v[i % dim] = 1.0
    return v


def test_memory_store_top1_is_exact_match():
    store = MemoryVectorStore(dim=8)
    chunks = _chunks(4)
    store.add(chunks, [_one_hot(8, i) for i in range(4)])
    hits = store.search(_one_hot(8, 2), k=2)
    assert hits[0].chunk.chunk_id == "d2#0000"
    assert hits[0].score == pytest.approx(1.0)


def test_memory_store_dim_mismatch_rejected():
    store = MemoryVectorStore(dim=4)
    with pytest.raises(ValueError):
        store.add(_chunks(1), [_one_hot(8, 0)])
    with pytest.raises(ValueError):
        store.search(_one_hot(8, 0), k=1)


def test_memory_reset():
    store = MemoryVectorStore(dim=4)
    store.add(_chunks(2), [_one_hot(4, i) for i in range(2)])
    assert store.count() == 2
    store.reset()
    assert store.count() == 0
    assert store.search(_one_hot(4, 0), k=5) == []


def test_faiss_store_matches_memory_when_available():
    faiss = pytest.importorskip("faiss")
    from worldrag.vector.faiss_impl import FaissVectorStore

    chunks = _chunks(5)
    vectors = [_one_hot(16, i) for i in range(5)]
    mem = MemoryVectorStore(dim=16)
    mem.add(chunks, vectors)

    fs = FaissVectorStore(dim=16)
    assert fs._error is None  # anti fake-green: real backend must be live
    fs.add(chunks, vectors)
    assert fs.count() == 5

    q = _one_hot(16, 3)
    assert fs.search(q, k=1)[0].chunk.chunk_id == mem.search(q, k=1)[0].chunk.chunk_id
    assert fs.search(q, k=1)[0].score == pytest.approx(1.0, abs=1e-5)
