"""Mock SQL service."""


class MockSQLService:
    """RealSQLService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def generate_and_query(self, question: str) -> dict:
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


_service = MockSQLService()


async def generate_and_query(question: str) -> dict:
    return await _service.generate_and_query(question)
