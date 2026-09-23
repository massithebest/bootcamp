"""폐쇄망 반입 후 구현할 Anthropic 호환 프록시 경로."""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["anthropic-proxy"])


@router.api_route(
    "/anthropic/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_anthropic(path: str):
    """폐쇄망 게이트웨이 전달 구현을 반입한 뒤 이 본문을 채운다."""

    raise HTTPException(
        status_code=501,
        detail="Anthropic 프록시는 폐쇄망 구현 반입 후 사용할 수 있습니다.",
    )
