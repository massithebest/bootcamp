"""사내 공통 SQL 실행 API 클라이언트 스텁.

폐쇄망 이식 대상이다. 반입되는 `common_sql_client.py`의 DB 연결·실행 로직을
여기에 병합한다(`docs/CLOSED_NETWORK_SETUP.md` §2-1, §2-4). 사내 IP는
하드코딩하지 않고 `core.config.COMMON_SQL_API_URL`에서 읽는다.
"""

from core.config import COMMON_SQL_API_URL, require_production_env


class CommonSqlClient:
    """사내 공통 SQL 실행 API를 호출하는 클라이언트."""

    async def execute(self, sql: str, *, row_limit: int) -> dict:
        """읽기 전용 SQL과 행 상한을 API에 전달하고 결과를 반환한다.

        이식한 HTTP 요청 본문은 API 계약에 맞춰 ``sql``과 ``rowLimit``을
        함께 보내야 한다. ``row_limit`` 값은 호출 서비스가 제공한다.

        이식 시 주의: 여기서는 가드레일을 재검사하지 않는다. 호출자인
        `services/production/sql_service.py`가 `services/sql/guard.py::check_sql`을
        먼저 통과시킨 SQL만 넘긴다는 계약을 유지한다.
        """

        require_production_env("COMMON_SQL_API_URL", COMMON_SQL_API_URL)

        # TODO: 폐쇄망 pntfp API에 {"sql": sql, "rowLimit": row_limit} 전송
        raise NotImplementedError(
            "CommonSqlClient.execute는 폐쇄망 이식 대상입니다. "
            "docs/CLOSED_NETWORK_SETUP.md §2-4 참고."
        )
