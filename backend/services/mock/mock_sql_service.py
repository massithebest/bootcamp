"""Mock SQL service — 합성 시드 SQLite 를 실제로 조회한다. (설계 §4)

더미 행을 만들지 않는다. 지식 → SQL → 결과 → 원인 판정 흐름을 실제 DB 없이도
끝까지 시험할 수 있어야 하기 때문이다.
"""

from __future__ import annotations

import logging
import sqlite3

from services.knowledge_service import get_store
from services.mock._sqlite import MISSING_DB_MESSAGE, SampleDbMissingError, connect
from services.sql_guard import MAX_ROWS, SqlGuardError, check_sql


logger = logging.getLogger(__name__)


def _error(message: str, sql: str) -> dict:
    return {"status": "error", "kind": "database", "message": message, "sql": sql}


class MockSQLService:
    """RealSQLService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def execute_sql(self, sql: str, purpose: str) -> dict:
        """카탈로그에 등록된 테이블을 SELECT 로 조회한다."""

        # purpose 는 실행 전에 남긴다 — 프론트 진행 표시와 사후 감사에 쓴다.
        logger.info("execute_sql purpose=%s", purpose)

        try:
            guarded_sql = check_sql(sql, get_store().table_names())
        except SqlGuardError as exc:
            return _error(str(exc), sql)

        try:
            conn = connect()
        except SampleDbMissingError:
            return _error(MISSING_DB_MESSAGE, sql)

        try:
            with conn:
                cursor = conn.execute(guarded_sql)
                columns = [description[0] for description in cursor.description or []]
                fetched = cursor.fetchmany(MAX_ROWS + 1)
        except sqlite3.Error as exc:
            return _error(f"SQL 실행 오류: {exc}", sql)
        finally:
            conn.close()

        truncated = len(fetched) > MAX_ROWS
        rows = [list(row) for row in fetched[:MAX_ROWS]]

        return {
            "status": "ok",
            "kind": "database",
            "sql": sql,
            "purpose": purpose,
            "table": {"columns": columns, "rows": rows},
            "row_count": len(rows),
            "truncated": truncated,
        }


_service = MockSQLService()


async def execute_sql(sql: str, purpose: str) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose)
