"""SQL tool for structured production planning data."""

from services import sql_service


async def execute_sql(sql: str, purpose: str) -> dict:
    """Run a read-only SQL query against the production planning database.

    SELECT 전용이며, 카탈로그(`list_tables` / `describe_table`)에 등록된
    테이블만 조회할 수 있다. 최대 500행까지 돌려주고, 초과하면 `truncated`
    가 true 로 온다.

    Args:
        sql: 실행할 SELECT 문.
        purpose: 이 쿼리로 확인하려는 것 한 줄. 진행 표시와 감사 로그에 쓴다.
    """

    return await sql_service.execute_sql(sql=sql, purpose=purpose)
