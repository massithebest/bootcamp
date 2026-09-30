"""Production SQL query service."""

from services.knowledge.catalog import get_store
from services.production.common_sql_client import CommonSqlClient
from services.service_logging import logged_service_operation
from services.sql.guard import MAX_ROWS, SqlGuardError, check_sql


def _error(message: str, sql: str) -> dict:
    return {"status": "error", "kind": "database", "message": message, "sql": sql}


class ProductionSQLService:
    """사내 DB 조회를 담당하는 실제 SQL 서비스."""

    def __init__(self, client: CommonSqlClient | None = None) -> None:
        self.client = client or CommonSqlClient()

    async def execute_sql(
        self, sql: str, purpose: str, *, access_scope: str | None = None
    ) -> dict:
        """Execute a read-only SQL query against the production planning DB.

        가드레일로 SQL을 검증한 뒤 조회 API에 `rowLimit=MAX_ROWS`를 전달한다.
        """

        allowed_tables = get_store().table_names()
        try:
            guarded_sql = check_sql(sql, allowed_tables)
        except SqlGuardError as exc:
            return _error(str(exc), sql)

        return await self.client.execute(guarded_sql, row_limit=MAX_ROWS)


_service = ProductionSQLService()


@logged_service_operation
async def execute_sql(sql: str, purpose: str, *, access_scope: str | None = None) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose, access_scope=access_scope)
