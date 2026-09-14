"""Real SQL generation and database query service."""


class RealSQLService:
    """Text-to-SQL + DB 조회를 담당하는 실제 SQL 서비스."""

    async def generate_and_query(self, question: str) -> dict:
        """Generate SQL and query production planning database."""

        # TODO:
        # 폐쇄망의 실제 SQL Agent / DB Query 로직을 이식

        raise NotImplementedError(
            "Real SQL service must be implemented in the closed network."
        )


_service = RealSQLService()


async def generate_and_query(question: str) -> dict:
    return await _service.generate_and_query(question)
