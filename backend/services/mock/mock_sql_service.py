"""Mock SQL service — 합성 mock SQLite를 실제로 조회한다. (설계 §4)

더미 행을 만들지 않는다. 지식 → SQL → 결과 → 원인 판정 흐름을 실제 DB 없이도
끝까지 시험할 수 있어야 하기 때문이다.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from services.knowledge.catalog import get_store
from services.mock._sqlite import MISSING_DB_MESSAGE, MockDbMissingError, connect
from services.results.query import tool_preview
from services.results.store import get_result_store
from services.service_logging import logged_service_operation
from services.sql.guard import MAX_ROWS, SqlGuardError, check_sql


#: Agent 에게 알리는 SQL 방언. production sql_service 와 같은 이름으로 공개한다.
SQL_DIALECT = "SQLite"


def _error(message: str, sql: str) -> dict:
    return {"status": "error", "kind": "database", "message": message, "sql": sql}


class MockSQLService:
    """ProductionSQLService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def execute_sql(
        self, sql: str, purpose: str, *, access_scope: str | None = None
    ) -> dict:
        """카탈로그에 등록된 테이블을 SELECT 로 조회한다."""

        allowed_tables = get_store().table_names()
        try:
            guarded_sql = check_sql(sql, allowed_tables)
        except SqlGuardError as exc:
            return _error(str(exc), sql)

        try:
            conn = connect()
        except MockDbMissingError:
            return _error(MISSING_DB_MESSAGE, sql)

        allowed_lower = {name.lower() for name in allowed_tables}

        def authorize(action, table, _column, database, _trigger):
            # SQL 문자열 검사만으로 놓치는 인용 식별자/주석/CTE 내부 참조도
            # SQLite가 실제 읽는 테이블을 기준으로 확인한다.
            if action == sqlite3.SQLITE_READ and (
                database not in {"main", None} or table.lower() not in allowed_lower
            ):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        conn.set_authorizer(authorize)
        try:
            with conn:
                cursor = conn.execute(guarded_sql)
                columns = [description[0] for description in cursor.description or []]
                fetched = cursor.fetchmany(MAX_ROWS + 1)
        except sqlite3.Error as exc:
            return _error(f"SQL 실행 오류: {exc} (이 DB의 SQL 방언은 {SQL_DIALECT}입니다.)", sql)
        finally:
            conn.close()

        source_truncated = len(fetched) > MAX_ROWS
        rows = [list(row) for row in fetched[:MAX_ROWS]]
        meta = get_result_store().save(
            columns,
            rows,
            source="execute_sql",
            conversation_id=None,
            source_truncated=source_truncated,
            access_scope=access_scope,
        )

        return tool_preview(
            meta,
            pd.DataFrame(rows, columns=columns),
            kind="database",
            purpose=purpose,
        )


_service = MockSQLService()


@logged_service_operation
async def execute_sql(sql: str, purpose: str, *, access_scope: str | None = None) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose, access_scope=access_scope)
