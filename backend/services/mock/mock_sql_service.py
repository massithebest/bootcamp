"""Mock SQL service — 합성 시드 SQLite 를 실제로 조회한다. (설계 §4)

더미 행을 만들지 않는다. 지식 → SQL → 결과 → 원인 판정 흐름을 실제 DB 없이도
끝까지 시험할 수 있어야 하기 때문이다.
"""

from __future__ import annotations

import logging
import sqlite3

import pandas as pd

from services.chart_inference import infer_chart
from services.knowledge_service import get_store
from services.mock._sqlite import MISSING_DB_MESSAGE, SampleDbMissingError, connect
from services.result_store import get_result_store, summarize_dataframe
from services.sql_guard import MAX_ROWS, SqlGuardError, check_sql


logger = logging.getLogger(__name__)
INLINE_ROW_THRESHOLD = 100
SAMPLE_ROW_COUNT = 10


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

        rows = [list(row) for row in fetched[:MAX_ROWS]]
        meta = get_result_store().save(
            columns,
            rows,
            source="execute_sql",
            conversation_id=None,
        )

        result = {
            "status": "ok",
            "kind": "database",
            "type": "inline" if len(rows) <= INLINE_ROW_THRESHOLD else "large_result",
            "result_id": meta.result_id,
            "sql": sql,
            "purpose": purpose,
            "row_count": len(rows),
        }
        if len(rows) <= INLINE_ROW_THRESHOLD:
            result["table"] = {"columns": columns, "rows": rows}
        else:
            result["columns"] = [
                {"name": column.name, "dtype": column.dtype, "role": column.role}
                for column in meta.columns
            ]
            result["sample_rows"] = rows[:SAMPLE_ROW_COUNT]
            result["summary"] = summarize_dataframe(pd.DataFrame(rows, columns=columns))
        chart = infer_chart(columns, rows)
        if chart is not None:
            result["chart"] = chart
        return result


_service = MockSQLService()


async def execute_sql(sql: str, purpose: str) -> dict:
    return await _service.execute_sql(sql=sql, purpose=purpose)
