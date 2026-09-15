"""검증된 차트 v2 명세를 등록하는 에이전트 Tool."""

from __future__ import annotations

from services.visualization_models import VisualizationRequest
from services.visualization_service import VisualizationError, prepare_visualization as prepare


async def prepare_visualization(
    result_id: str,
    kind: str,
    x: str,
    y: list[str],
    group_by: str | None = None,
    *,
    access_scope: str | None = None,
) -> dict:
    """result_id와 표현 명세만 받아 검증된 visualization_id를 발급한다."""

    try:
        meta = prepare(
            VisualizationRequest(
                result_id=result_id,
                kind=kind,
                x=x,
                y=tuple(y) if isinstance(y, list) else (),
                group_by=group_by,
            ),
            access_scope=access_scope,
        )
    except VisualizationError as exc:
        return exc.as_tool_result()
    return {
        "status": "ok",
        "visualization_id": meta.visualization_id,
        "warnings": [
            {"code": warning.code, "message": warning.message}
            for warning in meta.warnings
        ],
    }
