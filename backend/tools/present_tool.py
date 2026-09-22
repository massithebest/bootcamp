"""모델이 조합한 결과 UI 트리를 검증하는 Agent Tool."""

from __future__ import annotations

from typing import Any

from services.present_service import PresentError, validate_present


async def present(node: dict[str, Any], *, access_scope: str | None = None) -> dict:
    """UI 트리를 검증한다. 성공하면 ``{}``, 실패하면 안전한 오류 payload를 반환한다.

    `access_scope`는 모델에게 노출하지 않고 `agent/sdk_tools.py`의 wrapper가 채운다.
    """

    try:
        return validate_present(node, access_scope=access_scope)
    except PresentError as exc:
        return exc.as_tool_result()
