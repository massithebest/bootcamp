"""Mock adapter uses the same approved local documents; no fabricated hits."""
from asyncio import to_thread
from services.document_store import get_document_store
from services.service_logging import logged_service_operation


class MockRAGService:
    async def search(self, query: str) -> dict:
        return await to_thread(get_document_store().search, query)


_service = MockRAGService()


@logged_service_operation
async def search(query: str) -> dict:
    return await _service.search(query)
