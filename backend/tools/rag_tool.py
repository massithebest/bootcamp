"""RAG tool for production planning knowledge search."""

from services import rag_service


async def search_knowledge(query: str) -> dict:
    """Search production planning knowledge.

    Use this tool for:
    - process manuals
    - business terminology
    - production planning policies
    - non-structured domain knowledge
    """

    return await rag_service.search(query)
