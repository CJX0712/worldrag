"""Download the ONNX reranker model from ModelScope (HF is unreachable from
this network). Model files land in models/ which is git-ignored.

Usage: python scripts/download_models.py

Author: 晨星
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

REPO = "AI-ModelScope/bge-reranker-v2-m3"
FILES = ["model.onnx", "tokenizer.json", "config.json"]
DEST = Path(__file__).resolve().parents[1] / "models" / "bge-reranker-v2-m3"


def download(repo: str, name: str, dest: Path) -> None:
    url = f"https://www.modelscope.cn/api/v1/models/{repo}/repo?Revision=master&FilePath={name}"
    print(f"downloading {name} ...")
    with urllib.request.urlopen(url, timeout=300) as resp, open(dest, "wb") as fh:
        while True:
            block = resp.read(1 << 20)
            if not block:
                break
            fh.write(block)
    print(f"  -> {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = DEST / name
        if target.exists() and target.stat().st_size > 0:
            print(f"skip {name} (exists)")
            continue
        download(REPO, name, target)
    print("done. set WORLDRAG_RERANK_BACKEND=onnx to enable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
