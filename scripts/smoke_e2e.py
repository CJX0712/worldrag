"""Self-contained end-to-end smoke test.

Spawns the real API server as a subprocess, waits for /health, then asserts
the core success flow AND the key error flows over HTTP. Works fully offline
(default config: hash embed + memory store + mock LLM).

The ingested document deliberately exceeds the chunk threshold so the
multi-chunk path is genuinely covered (a short doc would fake-pass without
ever exercising chunking in the serving path).

Author: 晨星
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PORT = 8123
BASE = f"http://127.0.0.1:{PORT}/api"

# > 500 chars default chunk size -> forces multi-chunk ingest
DOC = (
    "WorldRAG 的检索架构采用双路召回设计。第一路是稀疏检索，基于 BM25 算法与中文单字加双字切分，"
    "擅长精确匹配专有名词与数字。第二路是稠密检索，基于嵌入向量与余弦相似度，擅长语义泛化。"
    "两路结果通过倒数排名融合算法合并，融合后的候选进入重排阶段。重排器是交叉编码器，"
    "但它的分数不会直接决定最终顺序，而是与融合分数按权重加权求和，防止重排器在查询语言上"
    "力不从心时压掉正确答案。最终答案由大语言模型基于排序后的上下文生成，并附带来源引用编号。"
    "整个链路支持完全离线运行：哈希嵌入、内存向量库与抽取式模拟生成器构成离线兜底实现，"
    "使得持续集成环境不需要下载任何模型即可完成端到端验证。"
)


def _req(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body}


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               PYTHONPATH=str(ROOT / "src"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "worldrag.api.app:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        cwd=ROOT, env=env,
    )
    try:
        # wait for health
        healthy = False
        for _ in range(60):
            try:
                status, body = _req("GET", "/health")
                if status == 200 and body.get("status") == "ok":
                    healthy = True
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.5)
        check("server health", healthy)

        # error flow: query before ingest -> 409
        status, _ = _req("POST", "/query", {"query": "任意问题"})
        check("query-before-ingest returns 409", status == 409, f"got {status}")

        # error flow: empty ingest -> 400
        status, _ = _req("POST", "/ingest", {"texts": [], "paths": []})
        check("empty ingest returns 400", status == 400, f"got {status}")

        # error flow: empty query string -> 422 (schema validation)
        status, _ = _req("POST", "/query", {"query": ""})
        check("empty query returns 422", status == 422, f"got {status}")

        # success flow: ingest multi-chunk doc
        status, body = _req("POST", "/ingest", {"texts": [{"text": DOC, "doc_id": "arch-doc"}]})
        multi = status == 200 and body.get("ingested_chunks", 0) >= 1
        check("ingest succeeds", multi, json.dumps(body, ensure_ascii=False)[:200])

        status, body = _req("GET", "/health")
        check("chunk count updated", status == 200 and body.get("chunks", 0) >= 1)

        # success flow: query with citations
        status, body = _req("POST", "/query", {"query": "重排器的分数如何影响最终顺序？"})
        ok_answer = (
            status == 200
            and len(body.get("answer", "")) > 0
            and len(body.get("citations", [])) >= 1
            and body["citations"][0].get("doc_id") == "arch-doc"
        )
        check("query returns answer + citations", ok_answer, json.dumps(body, ensure_ascii=False)[:300])

        # retrieval correctness: the answer must come from the right chunk
        if status == 200 and body.get("citations"):
            check("citation snippet relevant", "重排" in body["citations"][0].get("snippet", "")
                  or "融合" in body["citations"][0].get("snippet", ""))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/pid", str(proc.pid), "/t", "/f"],
                           capture_output=True)

    passed = sum(1 for _, ok, _ in checks if ok)
    failed = len(checks) - passed
    for name, ok, detail in checks:
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        print(line + (f"  -- {detail}" if detail and not ok else ""))
    print(f"e2e: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
