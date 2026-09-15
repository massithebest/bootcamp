"""Chat API endpoint with SSE streaming."""

import re

from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agent.agent import run_agent
from api.schemas import ChatRequest
from core.config import SESSION_COOKIE_SECURE, SESSION_SCOPE_COOKIE_NAME


router = APIRouter()
_SCOPE_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@router.post("/chat")
async def chat(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """Run the production planning agent and stream AgentEvents via SSE."""

    access_scope = http_request.cookies.get(SESSION_SCOPE_COOKIE_NAME)
    issue_cookie = access_scope is None or not _SCOPE_PATTERN.fullmatch(access_scope)
    if issue_cookie:
        access_scope = uuid4().hex

    async def event_generator():
        try:
            async for event in run_agent(
                message=request.message,
                conversation_id=request.conversation_id,
                fork_from_turn_id=request.fork_from_turn_id,
                access_scope=access_scope,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

        except Exception:
            # TODO:
            # 실제 환경에서는 내부 오류를 logging 한다.
            # 상세 Exception 내용은 Frontend에 그대로 노출하지 않는다.
            yield (
                'data: {"type":"error",'
                '"content":"Agent 실행 중 오류가 발생했습니다."}\n\n'
            )

            yield 'data: {"type":"done"}\n\n'

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    if issue_cookie:
        response.set_cookie(
            key=SESSION_SCOPE_COOKIE_NAME,
            value=access_scope,
            httponly=True,
            samesite="lax",
            secure=SESSION_COOKIE_SECURE,
            path="/",
        )
    return response
