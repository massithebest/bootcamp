"""저장된 조회 결과의 preview·table·chart 조회 API (읽기 전용)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response

from api.schemas import QueryChartResponse, QueryPreviewResponse, QueryTableResponse
from core.config import SESSION_SCOPE_COOKIE_NAME
from services.query_result_errors import QueryResultError
from services.query_result_service import read_chart, read_preview, read_table
from services.result_store import get_result_store


router = APIRouter()


def _http_error(error: QueryResultError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


def _scope(request: Request) -> str | None:
    return request.cookies.get(SESSION_SCOPE_COOKIE_NAME)


def _cache_headers(response: Response, result_id: str) -> None:
    """결과는 TTL 동안 불변이므로 남은 수명만큼 private 캐시를 허용한다."""

    max_age = 0
    try:
        meta = get_result_store().get_meta(result_id)
        if meta is not None:
            remaining = (meta.expires_at - datetime.now(timezone.utc)).total_seconds()
            max_age = max(0, int(remaining))
    except Exception:
        max_age = 0
    response.headers["Cache-Control"] = f"private, max-age={max_age}"
    response.headers["Vary"] = "Cookie"


@router.get("/query-results/{result_id}/preview", response_model=QueryPreviewResponse)
async def get_preview(result_id: str, request: Request, response: Response) -> dict[str, Any]:
    try:
        payload = read_preview(result_id, access_scope=_scope(request))
    except QueryResultError as exc:
        raise _http_error(exc) from None
    _cache_headers(response, result_id)
    return payload


@router.get("/query-results/{result_id}/table", response_model=QueryTableResponse)
async def get_table(
    result_id: str,
    request: Request,
    response: Response,
    page: str | None = Query(default=None),
    page_size: str | None = Query(default=None),
    columns: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_column: str | None = Query(default=None),
    sort_direction: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        payload = read_table(
            result_id,
            page=page,
            page_size=page_size,
            columns=columns,
            search=search,
            sort_column=sort_column,
            sort_direction=sort_direction,
            access_scope=_scope(request),
        )
    except QueryResultError as exc:
        raise _http_error(exc) from None
    _cache_headers(response, result_id)
    return payload


@router.get("/query-results/{result_id}/chart", response_model=QueryChartResponse)
async def get_chart(
    result_id: str,
    request: Request,
    response: Response,
    chart_type: str | None = Query(default=None),
    x_column: str | None = Query(default=None),
    y_column: str | None = Query(default=None),
    group_by_column: str | None = Query(default=None),
    aggregation: str | None = Query(default=None),
    title: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        payload = read_chart(
            result_id,
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            group_by_column=group_by_column,
            aggregation=aggregation,
            title=title,
            access_scope=_scope(request),
        )
    except QueryResultError as exc:
        raise _http_error(exc) from None
    _cache_headers(response, result_id)
    return payload
