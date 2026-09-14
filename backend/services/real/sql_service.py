"""Real SQL query service."""


class RealSQLService:
    """사내 DB 조회를 담당하는 실제 SQL 서비스."""

    async def execute_sql(self, sql: str, purpose: str) -> dict:
        """Execute a read-only SQL query against the production planning DB.

        이식 시 주의: mock 과 동일한 가드레일(`services/sql_guard.check_sql`)을
        반드시 통과시킨 뒤 실행한다. 가드레일은 서비스 계층 책임이며 mock/real
        양쪽에서 같은 규칙으로 동작해야 한다 (docs/domain-knowledge.md §4).
        """

        # TODO:
        # 폐쇄망의 실제 pntfp DB 연결 후 동일 가드레일 적용

        raise NotImplementedError(
            "Real SQL service must be implemented in the closed network."
        )


_service = RealSQLService()


async def execute_sql(sql: str, purpose: str) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose)
