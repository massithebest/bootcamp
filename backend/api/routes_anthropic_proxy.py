"""Claude Code CLI 가 호출하는 Anthropic 호환 프록시 경로.

- LLM_PROVIDER=azure_openai: Azure OpenAI 호환 게이트웨이로 변환해 전달한다.
- 그 외(LLM_PROVIDER=local 포함): 폐쇄망 게이트웨이 전달 구현을 반입하기 전까지 501.
"""

import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core import config
from services.llm import azure_openai_proxy

router = APIRouter(tags=["anthropic-proxy"])


def _authorized(request: Request) -> bool:
    """CLI 에 주입한 프로세스별 토큰만 허용한다(x-api-key 또는 Bearer)."""

    supplied = request.headers.get("x-api-key") or ""
    authorization = request.headers.get("authorization") or ""
    if authorization.lower().startswith("bearer "):
        supplied = supplied or authorization[7:]
    return bool(supplied) and secrets.compare_digest(supplied, config.LOCAL_PROXY_TOKEN)


@router.api_route(
    "/anthropic/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_anthropic(path: str, request: Request):
    if config.LLM_PROVIDER != "azure_openai":
        raise HTTPException(
            status_code=501,
            detail="Anthropic 프록시는 폐쇄망 구현 반입 후 사용할 수 있습니다.",
        )
    if not _authorized(request):
        return JSONResponse(azure_openai_proxy.anthropic_error("인증되지 않은 요청입니다.", "authentication_error"),
                            status_code=401)

    route = (request.method, path.strip("/"))
    if route not in {("POST", "v1/messages"), ("POST", "v1/messages/count_tokens")}:
        return JSONResponse(azure_openai_proxy.anthropic_error("지원하지 않는 경로입니다.", "not_found_error"),
                            status_code=404)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse(azure_openai_proxy.anthropic_error("요청 본문이 JSON 이 아닙니다.", "invalid_request_error"),
                            status_code=400)

    try:
        if route[1] == "v1/messages/count_tokens":
            return {"input_tokens": azure_openai_proxy.estimate_tokens(body)}
        if body.get("stream"):
            events = await azure_openai_proxy.open_message_stream(body)
            return StreamingResponse(events, media_type="text/event-stream",
                                     headers={"cache-control": "no-cache"})
        return await azure_openai_proxy.create_message(body)
    except azure_openai_proxy.ProxyError as error:
        status = error.status_code if 400 <= error.status_code < 600 else 502
        return JSONResponse(azure_openai_proxy.anthropic_error(error.message), status_code=status)
