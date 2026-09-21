import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
import pytest

from core import config
from main import app
from services.document_store import DocumentStore, KnowledgeError
from services.knowledge_service import get_store
from agent.sdk_tools import TOOL_NAMES, build_planning_mcp_server
from mcp_types import PaginatedRequestParams
from tools.rag_tool import search_documents

FIELDS = dict(title="리드타임 정책", content="승인된 리드타임은 작업 시작부터 완료까지의 시간입니다.", category="정책", tags=["리드타임"], owner="담당자", source="검토 회의")


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / "knowledge.sqlite3"
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", path)
    monkeypatch.setattr(config, "KNOWLEDGE_SEARCH_BACKEND", "local")
    return DocumentStore(path)


def publish(store, fields=FIELDS):
    doc = store.save(fields)
    doc = store.transition(doc["id"], "review", doc["revision"], version=1, actor="검토자", note="업무 정의 확인")
    return store.transition(doc["id"], "activate", doc["revision"], version=1, actor="검토자")


def test_versions_publish_deactivate_archive_and_restart(store):
    doc = store.save(FIELDS)
    key = doc["id"]
    assert store.search("리드타임")["documents"] == []
    with pytest.raises(KnowledgeError, match="검토 완료"):
        store.transition(key, "activate", 1, version=1)
    doc = store.transition(key, "review", 1, version=1, actor="검토자", note="정의 확인")
    assert store.search("리드타임")["documents"] == []
    doc = store.transition(key, "activate", doc["revision"], version=1)
    doc = store.save({**FIELDS, "content": "새 정책 변경 내용"}, key, doc["revision"])
    assert store.search("리드타임")["documents"][0]["version"] == 1
    restarted = DocumentStore(store.path)
    assert restarted.get(key) == doc
    doc = restarted.transition(key, "review", doc["revision"], version=2, actor="검토자", note="새 정책 확인")
    doc = restarted.transition(key, "activate", doc["revision"], version=2)
    assert restarted.search("리드타임")["documents"][0]["version"] == 2
    doc = restarted.transition(key, "deactivate", doc["revision"])
    assert restarted.search("리드타임")["documents"] == []
    doc = restarted.transition(key, "archive", doc["revision"])
    assert len(doc["versions"]) == 2 and doc["versions"][1]["content"] == FIELDS["content"]
    with pytest.raises(KnowledgeError, match="보관"):
        restarted.save(FIELDS, key, doc["revision"])


def test_revision_conflicts_are_atomic(store):
    doc = publish(store)
    def save_one(index):
        try:
            return store.save({**FIELDS, "title": str(index)}, doc["id"], doc["revision"])
        except KnowledgeError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save_one, [1, 2]))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    assert len(store.get(doc["id"])["versions"]) == 2


def test_korean_search_empty_normalization_and_filters(store):
    publish(store)
    publish(store, {**FIELDS, "title": "ＷＩＰ 기준", "content": "재공 관리", "tags": ["WIP"]})
    assert len(store.search("리드타임 정의 알려줘")["documents"]) == 1
    assert store.search("wip")["documents"][0]["title"] == "ＷＩＰ 기준"
    for query in ("", "?!", "없는검색어"):
        assert store.search(query)["documents"] == []
    store.save({**FIELDS, "title": "초안만", "content": "기밀초안"})
    assert store.search("기밀초안")["documents"] == []
    assert "score" not in store.search("리드타임")["documents"][0]
    assert asyncio.run(search_documents("리드타임"))["kind"] == "knowledge"


def test_management_api_validation_history_and_safe_errors(store, monkeypatch):
    client = TestClient(app)
    assert client.post("/api/knowledge/documents", json={**FIELDS, "title": " "}).status_code == 422
    doc = client.post("/api/knowledge/documents", json=FIELDS).json()
    url = f"/api/knowledge/documents/{doc['id']}"
    assert client.post(url + "/review", json={"expected_revision": 1, "version": 1, "actor": "x", "note": ""}).status_code == 422
    doc = client.post(url + "/review", json={"expected_revision": 1, "version": 1, "actor": "x", "note": "確認"}).json()
    assert client.put(url, json={**FIELDS, "expected_revision": 1}).status_code == 409
    assert client.get(url + "/versions/1").json()["content"] == FIELDS["content"]
    assert client.get(url + "/versions/99").status_code == 404
    assert client.get("/api/knowledge/entries?q=작업 시작").json()[0]["id"] == doc["id"]
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", store.path.parent)  # a directory is not a database
    response = client.get("/api/knowledge/documents")
    assert response.status_code == 503
    assert str(store.path.parent) not in response.text


@pytest.mark.usefixtures("bundled_knowledge")
def test_catalog_matches_sdk_wire_and_structured_readonly(store):
    client = TestClient(app)
    rows = client.get("/api/knowledge/tools").json()
    server = build_planning_mcp_server()["instance"]
    wire = asyncio.run(server._request_handlers["tools/list"].handler(None, PaginatedRequestParams()))
    assert {"mcp__planning__" + row["name"] for row in rows} == set(TOOL_NAMES)
    assert {r["name"]: r["input_schema"] for r in rows} == {r.name: r.input_schema for r in wire.tools}
    assert len(rows) == 14
    entries = client.get("/api/knowledge/entries").json()
    assert {e["type"] for e in entries} >= {"table", "kpi", "recipe", "glossary", "simulation"}
    assert all(e["active"] is True for e in entries)
    detail = client.get("/api/knowledge/entries/kpi/initial_wip").json()
    assert detail["detail"] == get_store().kpis["initial_wip"].model_dump(mode="json")
    table_detail = client.get("/api/knowledge/entries/table/wip").json()["detail"]
    assert set(table_detail["sample_queries"][0]) == {"question", "sql"}
    assert table_detail["query_rules"]
    assert table_detail["visualization_hints"]
    assert client.put("/api/knowledge/entries/kpi/initial_wip", json={}).status_code == 405
    assert client.get("/api/knowledge/skills/sql-analysis").json()["content"]


def test_mock_search_returns_published_version(store):
    from services.mock import mock_rag_service

    doc = publish(store)

    result = asyncio.run(mock_rag_service.search("리드타임 정책 알려줘"))

    assert result["documents"][0]["document_id"] == doc["id"]
    assert result["documents"][0]["version"] == 1


def test_sqlite_backup_preserves_published_revision(store, tmp_path):
    import sqlite3
    original = publish(store)
    backup_path = tmp_path / "backup.sqlite3"
    with sqlite3.connect(store.path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    restored = DocumentStore(backup_path)
    assert restored.get(original["id"]) == original
    assert restored.search("리드타임") == store.search("리드타임")
