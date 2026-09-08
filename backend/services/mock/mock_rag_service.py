"""Mock RAG service."""


async def search(query: str) -> dict:
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
