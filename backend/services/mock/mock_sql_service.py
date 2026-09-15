"""Mock SQL service — SMT2020 SQLite를 실제로 조회한다. (설계 §4)

더미 행을 만들지 않는다. 지식 → SQL → 결과 → 원인 판정 흐름을 실제 DB 없이도
끝까지 시험할 수 있어야 하기 때문이다.
"""

from __future__ import annotations

import logging
import sqlite3

import pandas as pd

from services.knowledge_service import get_store
from services.mock._sqlite import MISSING_DB_MESSAGE, Smt2020DbMissingError, connect
from services.result_store import get_result_store, summarize_dataframe
from services.sql_guard import MAX_ROWS, SqlGuardError, check_sql


logger = logging.getLogger(__name__)
INLINE_ROW_THRESHOLD = 100
SAMPLE_ROW_COUNT = 10


def _error(message: str, sql: str) -> dict:
    return {"status": "error", "kind": "database", "message": message, "sql": sql}


class MockSQLService:
    """RealSQLService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def execute_sql(
        self, sql: str, purpose: str, *, access_scope: str | None = None
    ) -> dict:
        """카탈로그에 등록된 테이블을 SELECT 로 조회한다."""

        # purpose 는 실행 전에 남긴다 — 프론트 진행 표시와 사후 감사에 쓴다.
        logger.info("execute_sql purpose=%s", purpose)

        allowed_tables = get_store().table_names()
        try:
            guarded_sql = check_sql(sql, allowed_tables)
        except SqlGuardError as exc:
            return _error(str(exc), sql)

        try:
            conn = connect()
        except Smt2020DbMissingError:
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
            return _error(f"SQL 실행 오류: {exc}", sql)
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

        result = {
            "status": "ok",
            "kind": "database",
            "type": "inline" if len(rows) <= INLINE_ROW_THRESHOLD else "large_result",
            "result_id": meta.result_id,
            "sql": sql,
            "purpose": purpose,
            "row_count": len(rows),
            "columns": [
                {"name": column.name, "dtype": column.dtype, "role": column.role}
                for column in meta.columns
            ],
        }
        if len(rows) <= INLINE_ROW_THRESHOLD:
            result["table"] = {"columns": columns, "rows": rows}
        else:
            result["sample_rows"] = rows[:SAMPLE_ROW_COUNT]
            result["summary"] = summarize_dataframe(pd.DataFrame(rows, columns=columns))
        return result


_service = MockSQLService()


async def execute_sql(sql: str, purpose: str, *, access_scope: str | None = None) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose, access_scope=access_scope)
