"""Self-contained production-path evaluation.

Starts `ollama serve` as a child process, waits for readiness, runs the
evaluation against the real backends (Ollama embed + faiss + Ollama LLM),
then tears the server down. Avoids shell-level process spawning quirks.

Author: 晨星
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

OLLAMA = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
BASE = "http://localhost:11434"


def wait_ready(timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/tags", timeout=3):
                return True
        except OSError:
            time.sleep(1.0)
    return False


def main() -> int:
    serve = subprocess.Popen(
        [OLLAMA, "serve"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_ready():
            print(json.dumps({"error": "ollama serve not ready"}, ensure_ascii=False))
            return 1

        os.environ.update({
            "WORLDRAG_EMBED_BACKEND": "ollama",
            "WORLDRAG_VECTOR_BACKEND": "faiss",
            "WORLDRAG_LLM_BACKEND": "ollama",
        })
        from worldrag.config import Config
        from worldrag.evaluate.runner import load_gold, run_evaluation
        from worldrag.ingest.loaders import load_directory

        cfg = Config()
        started = time.time()
        result = run_evaluation(
            load_directory(os.path.join(ROOT, "data", "samples")),
            load_gold(os.path.join(ROOT, "eval", "gold.jsonl")),
            cfg,
        )
        result["elapsed_sec"] = round(time.time() - started, 1)
        print("PROD_EVAL " + json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        serve.terminate()
        try:
            serve.wait(timeout=10)
        except subprocess.TimeoutExpired:
            serve.kill()


if __name__ == "__main__":
    raise SystemExit(main())
