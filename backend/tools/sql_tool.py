"""SQL tool for structured production planning data."""

from services import sql_service


async def execute_sql(sql: str, purpose: str, *, access_scope: str | None = None) -> dict:
    """Run a read-only SQL query against the production planning database.

    SELECT 전용이며, 카탈로그(`list_tables` / `describe_table`)에 등록된
    테이블만 조회할 수 있다. 결과는 저장소에 보관되며, 100행 이하는 표 전체를,
    초과 결과는 ``result_id``와 샘플·요약을 돌려준다. SQL 가드레일은 최대
    500행을 허용한다.

    Args:
        sql: 실행할 SELECT 문.
        purpose: 이 쿼리로 확인하려는 것 한 줄. 진행 표시와 감사 로그에 쓴다.
        access_scope: 요청 브라우저 세션의 불투명 scope. 모델에게 노출하지
            않고 `agent/sdk_tools.py`의 tool wrapper가 내부에서 채운다.
    """

    return await sql_service.execute_sql(sql=sql, purpose=purpose, access_scope=access_scope)
