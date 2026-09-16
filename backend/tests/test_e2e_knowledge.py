"""Opt-in actual provider check; uses only an isolated synthetic document."""
import asyncio
import os

import pytest

from core import config
from services.document_store import DocumentStore

pytestmark = pytest.mark.e2e


def test_real_agent_searches_and_cites_published_document(tmp_path, monkeypatch):
    if not config.CLAUDE_CLI_PATH or not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
        pytest.skip("CLI/provider credentials are not configured")
    monkeypatch.delenv("PLANNING_AGENT_FAKE", raising=False)
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(config, "KNOWLEDGE_SEARCH_BACKEND", "local")
    store = DocumentStore(config.KNOWLEDGE_DB_PATH)
    doc = store.save(dict(title="ZETA 검증 정책", content="ZETA 검증 정책의 확인 코드는 CHECK-742입니다.", category="검증", tags=["ZETA"], owner="테스트", source="합성 E2E 검증 자료"))
    doc = store.transition(doc["id"], "review", 1, version=1, actor="테스트", note="합성 fixture")
    store.transition(doc["id"], "activate", doc["revision"], version=1, actor="테스트")
    from agent.agent import run_agent
    async def collect():
        return [event async for event in run_agent("search_knowledge로 ZETA 검증 정책을 찾아 확인 코드와 문서 제목, 출처, 버전을 알려줘.")]
    events = asyncio.run(asyncio.wait_for(collect(), timeout=150))
    errors = [e for e in events if e.type == "error"]
    assert not errors, "Agent returned a public error"
    results = [e.data for e in events if e.type == "tool_result" and e.tool_name == "search_knowledge"]
    assert results and any(d.get("document_id") == doc["id"] and d.get("version") == 1 for r in results for d in r.get("documents", []))
    answer = "".join(e.content or "" for e in events)
    assert "CHECK-742" in answer and "ZETA" in answer
    assert "합성 E2E 검증 자료" in answer and "1" in answer
