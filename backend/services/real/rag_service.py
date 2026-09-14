"""Real production planning knowledge search service."""


class RealRAGService:
    """Milvus / Hybrid Search 기반 실제 RAG 서비스."""

    async def search(self, query: str) -> dict:
        """Search production planning knowledge from Milvus."""

        # TODO:
        # 폐쇄망의 기존 Milvus / Hybrid Search 로직 이식

        raise NotImplementedError(
            "Real RAG service must be implemented in the closed network."
        )


_service = RealRAGService()


async def search(query: str) -> dict:
    return await _service.search(query)
