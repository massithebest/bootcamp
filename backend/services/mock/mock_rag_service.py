"""Mock RAG service."""


class MockRAGService:
    """RealRAGService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def search(self, query: str) -> dict:
        """Return mock knowledge search result."""

        return {
            "status": "ok",
            "query": query,
            "documents": [
                {
                    "title": "공정 매뉴얼 v1",
                    "content": "더미 문서 내용",
                    "score": 0.82,
                }
            ],
        }


_service = MockRAGService()


async def search(query: str) -> dict:
    return await _service.search(query)
