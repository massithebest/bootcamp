"""Mock SQL service."""


async def generate_and_query(question: str) -> dict:
    """Return mock SQL query result."""

    return {
        "status": "ok",
        "question": question,
        "generated_sql": (
            "SELECT * FROM production_result LIMIT 10;"
        ),
        "rows": [
            {
                "line": "A",
                "date": "2026-09-01",
                "qty": 320,
            }
        ],
    }
