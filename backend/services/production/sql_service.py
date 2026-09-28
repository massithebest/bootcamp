"""Production SQL query service."""

from services.service_logging import logged_service_operation


class ProductionSQLService:
    """사내 DB 조회를 담당하는 실제 SQL 서비스."""

    async def execute_sql(
        self, sql: str, purpose: str, *, access_scope: str | None = None
    ) -> dict:
        """Execute a read-only SQL query against the production planning DB.

        이식 시 주의: mock 과 동일한 가드레일(`services/sql/guard.py::check_sql`)을
        반드시 통과시킨 뒤 실행한다. 가드레일은 서비스 계층 책임이며 mock/production
        양쪽에서 같은 규칙으로 동작해야 한다
        (backend/docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md).
        결과를 Result Store에 저장할 때 mock과 동일하게 source_truncated와
        access_scope를 채운다 (`plan/Todo.md`의 안정 계약 참고).
        """

        # TODO:
        # services/production/common_sql_client.py::CommonSqlClient.execute를 통해
        # 폐쇄망의 실제 pntfp DB에 연결하고 동일 가드레일을 적용한다.
        # docs/CLOSED_NETWORK_SETUP.md §2-4 참고.

        raise NotImplementedError(
            "Production SQL service must be implemented in the closed network."
        )


_service = ProductionSQLService()


@logged_service_operation
async def execute_sql(sql: str, purpose: str, *, access_scope: str | None = None) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose, access_scope=access_scope)
