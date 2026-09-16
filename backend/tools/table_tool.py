"""저장된 조회 결과를 대화형 표로 준비하는 Agent Tool."""

from __future__ import annotations

from services.table_service import TableError, prepare_table_payload


async def prepare_table(
    result_id: str,
    columns: list[str] | None = None,
    title: str | None = None,
    *,
    access_scope: str | None = None,
) -> dict:
    """result_id와 선택 표현만 받아 최대 100행 표 payload를 반환한다."""

    try:
        return prepare_table_payload(
            result_id,
            columns=columns,
            title=title,
            access_scope=access_scope,
        )
    except TableError as exc:
        return exc.as_tool_result()
