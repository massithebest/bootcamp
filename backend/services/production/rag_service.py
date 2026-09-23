"""Real production planning knowledge search service."""

from services.service_logging import logged_service_operation


class ProductionRAGService:
    """Milvus / Hybrid Search 기반 실제 RAG 서비스."""

    async def search(self, query: str) -> dict:
        """Search production planning knowledge from Milvus."""

        # TODO:
        # services/production/milvus_client.py::get_embedding_function,
        # get_milvus_client를 통해 폐쇄망의 기존 Milvus / Hybrid Search(dense +
        # BM25 > RRF > rerank) 로직을 이식한다. docs/CLOSED_NETWORK_SETUP.md §2-4 참고.

        raise NotImplementedError(
            "Real RAG service must be implemented in the closed network."
        )


_service = ProductionRAGService()


@logged_service_operation
async def search(query: str) -> dict:
    return await _service.search(query)
