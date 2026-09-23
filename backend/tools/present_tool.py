"""모델이 호출한 결과 표시용 Tool 인자를 검증하는 Agent Tool들."""

from __future__ import annotations

from typing import Any

from services.results.present import (
    PresentError,
    validate_present_chart,
    validate_present_simulation,
    validate_present_sql_preview,
    validate_present_table,
)


async def present_sql_preview(args: dict[str, Any], *, access_scope: str | None = None) -> dict:
    """SQL 원문 표시 설정을 검증한다. 성공하면 ``{}``, 실패하면 안전한 오류 payload를 반환한다."""

    try:
        return validate_present_sql_preview(args, access_scope=access_scope)
    except PresentError as exc:
        return exc.as_tool_result()


async def present_chart(args: dict[str, Any], *, access_scope: str | None = None) -> dict:
    """차트 표시 설정을 실제 저장 결과에 대해 검증한다."""

    try:
        return validate_present_chart(args, access_scope=access_scope)
    except PresentError as exc:
        return exc.as_tool_result()


async def present_table(args: dict[str, Any], *, access_scope: str | None = None) -> dict:
    """표 표시 설정을 실제 저장 결과에 대해 검증한다."""

    try:
        return validate_present_table(args, access_scope=access_scope)
    except PresentError as exc:
        return exc.as_tool_result()


async def present_simulation(args: dict[str, Any], *, access_scope: str | None = None) -> dict:
    """시뮬레이션 요약 표시 설정을 검증한다."""

    try:
        return validate_present_simulation(args, access_scope=access_scope)
    except PresentError as exc:
        return exc.as_tool_result()
