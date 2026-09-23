"""Knowledge search routing remains behind the service boundary."""

import asyncio

from core import config
from services import knowledge_search_service


def test_local_backend_uses_document_store_without_calling_rag_provider(monkeypatch) -> None:
    class Store:
        def search(self, query: str) -> dict:
            return {"kind": "knowledge", "status": "ok", "query": query}

    monkeypatch.setattr(config, "KNOWLEDGE_SEARCH_BACKEND", "local")
    monkeypatch.setattr(config, "SERVICE_MODE", "real")
    monkeypatch.setattr(knowledge_search_service, "get_document_store", Store)

    async def unexpected_provider_call(query: str) -> dict:
        raise AssertionError(f"provider must not be used for local search: {query}")

    monkeypatch.setattr(knowledge_search_service.rag_service, "search", unexpected_provider_call)

    result = asyncio.run(knowledge_search_service.search("리드타임"))

    assert result == {"kind": "knowledge", "status": "ok", "query": "리드타임"}


def test_nonlocal_backend_uses_selected_rag_service(monkeypatch) -> None:
    monkeypatch.setattr(config, "KNOWLEDGE_SEARCH_BACKEND", "vector")
    monkeypatch.setattr(knowledge_search_service, "get_document_store", lambda: None)
    calls: list[str] = []

    async def search_provider(query: str) -> dict:
        calls.append(query)
        return {"kind": "knowledge", "status": "ok", "query": query}

    monkeypatch.setattr(knowledge_search_service.rag_service, "search", search_provider)

    result = asyncio.run(knowledge_search_service.search("공정 기준"))

    assert result["status"] == "ok"
    assert calls == ["공정 기준"]
