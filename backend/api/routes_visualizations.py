"""검증된 차트 v2 시각화 조회 API."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from api.schemas import VisualizationResponse
from core.config import SESSION_SCOPE_COOKIE_NAME
from services.visualization_service import VisualizationError, read_visualization


router = APIRouter()

_NOT_FOUND_DETAIL = {
    "code": "RESULT_NOT_FOUND",
    "message": "시각화를 찾을 수 없습니다.",
}


def _http_error(error: VisualizationError) -> HTTPException:
    if error.code in {"RESULT_NOT_FOUND", "RESULT_FORBIDDEN"}:
        return HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL)
    if error.code in {"RESULT_EXPIRED", "RESULT_UNAVAILABLE"}:
        return HTTPException(
            status_code=410,
            detail={"code": error.code, "message": error.message},
        )
    return HTTPException(
        status_code=400,
        detail={"code": error.code, "message": error.message},
    )


@router.get(
    "/visualizations/{visualization_id}",
    response_model=VisualizationResponse,
)
async def get_visualization(
    visualization_id: str, request: Request, response: Response
) -> dict:
    """현재 브라우저 scope로 등록된 불변 시각화 payload를 반환한다."""

    access_scope = request.cookies.get(SESSION_SCOPE_COOKIE_NAME)
    try:
        payload = read_visualization(
            visualization_id,
            access_scope=access_scope,
        )
    except VisualizationError as exc:
        raise _http_error(exc) from None

    expires_at = datetime.fromisoformat(payload["expires_at"])
    max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    response.headers["Cache-Control"] = f"private, max-age={max_age}, immutable"
    response.headers["Vary"] = "Cookie"
    return payload
