"""Reranker implementations.

- PassThroughReranker: default; keeps RRF order (offline profile).
- OnnxReranker: cross-encoder via onnxruntime + tokenizers, model files
  pulled from ModelScope by scripts/download_models.py (HF is unreachable
  from this network). Blends CE scores into RRF order per ADR-002.

Author: 晨星
"""
from __future__ import annotations

from pathlib import Path

from worldrag.protocols import SearchResult
from worldrag.rerank.fusion import blend_scores


class PassThroughReranker:
    def __init__(self) -> None:
        pass

    @property
    def name(self) -> str:
        return "passthrough"

    def rerank(self, query: str, results: list[SearchResult], k: int) -> list[SearchResult]:
        return results[:k]


class OnnxReranker:
    def __init__(self, model_dir: str | Path, weight: float = 0.4) -> None:
        self._error: Exception | None = None
        model_dir = Path(model_dir)
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except Exception as exc:  # pragma: no cover
            self._error = exc
            raise RuntimeError(f"onnx reranker deps unavailable: {exc}") from exc
        model_path = model_dir / "model.onnx"
        tokenizer_path = model_dir / "tokenizer.json"
        if not model_path.exists() or not tokenizer_path.exists():
            self._error = FileNotFoundError(str(model_dir))
            raise RuntimeError(
                f"reranker model files missing under {model_dir}; "
                "run: python scripts/download_models.py"
            )
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        self._weight = weight

    @property
    def name(self) -> str:
        return f"onnx-cross-encoder(w={self._weight})"

    def _score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        import numpy as np

        encodings = [self._tokenizer.encode(q, d) for q, d in pairs]
        input_names = {i.name for i in self._session.get_inputs()}
        scores: list[float] = []
        for enc in encodings:
            feeds = {
                "input_ids": np.array([enc.ids], dtype=np.int64),
                "attention_mask": np.array([enc.attention_mask], dtype=np.int64),
                "token_type_ids": np.array([enc.type_ids], dtype=np.int64),
            }
            feeds = {k: v for k, v in feeds.items() if k in input_names}
            logits = self._session.run(None, feeds)[0]
            scores.append(float(logits.reshape(-1)[0]))
        return scores

    def rerank(self, query: str, results: list[SearchResult], k: int) -> list[SearchResult]:
        if not results:
            return []
        ce_scores = self._score_pairs([(query, r.chunk.text) for r in results])
        rrf_scores = [r.score for r in results]
        final = blend_scores(rrf_scores, ce_scores, self._weight)
        reranked = [
            SearchResult(chunk=r.chunk, score=f, source="rerank")
            for r, f in zip(results, final)
        ]
        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked[:k]
