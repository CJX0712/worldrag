"""API contract tests: success flow + error flows (in-process, offline).

Author: 晨星
"""
import pytest
from fastapi.testclient import TestClient

from worldrag.api.app import create_app
from worldrag.config import Config

DOC = "知识库系统的退款政策规定，年度套餐购买后十四天内可以无理由全额退款。" * 10


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(Config()))


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "backends" in body


def test_query_before_ingest_is_409(client):
    resp = client.post("/api/query", json={"query": "任意问题"})
    assert resp.status_code == 409


def test_empty_ingest_is_400(client):
    resp = client.post("/api/ingest", json={"texts": [], "paths": []})
    assert resp.status_code == 400


def test_empty_query_is_422(client):
    resp = client.post("/api/query", json={"query": ""})
    assert resp.status_code == 422


def test_ingest_then_query_flow(client):
    resp = client.post("/api/ingest", json={"texts": [{"text": DOC, "doc_id": "policy"}]})
    assert resp.status_code == 200
    assert resp.json()["ingested_chunks"] >= 1

    resp = client.post("/api/query", json={"query": "全额退款的期限是多久？"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["citations"][0]["doc_id"] == "policy"


def test_ingest_bad_path_is_400(client):
    resp = client.post("/api/ingest", json={"paths": ["C:/no/such/file.txt"]})
    assert resp.status_code == 400


def test_evaluate_endpoint_returns_metrics(client):
    resp = client.post("/api/evaluate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metrics"]["recall_at_k"] >= 0.5
    assert body["metrics"]["queries"] > 0
