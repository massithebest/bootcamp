"""SQL tool for structured production planning data."""

from services import sql_service


async def query_database(question: str) -> dict:
    """Query structured production planning data.

    Use this tool for:
    - production results
    - inventory
    - product information
    - equipment / line information
    - other structured business data
    """

    return await sql_service.generate_and_query(question)
