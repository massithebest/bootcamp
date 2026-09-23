"""Route approved knowledge search to the configured local or provider service."""

from asyncio import to_thread

from core import config
from services import rag_service
from services.document_store import get_document_store
from services.service_logging import logged_service_operation


@logged_service_operation
async def search(query: str) -> dict:
    """Search the local approved-document store or the configured RAG provider."""

    if config.KNOWLEDGE_SEARCH_BACKEND == "local":
        return await to_thread(get_document_store().search, query)
    return await rag_service.search(query)
