"""Chat API endpoint with SSE streaming."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agent.agent import run_agent
from api.schemas import ChatRequest


router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Run the production planning agent and stream AgentEvents via SSE."""

    async def event_generator():
        try:
            async for event in run_agent(
                message=request.message,
                conversation_id=request.conversation_id,
                fork_from_turn_id=request.fork_from_turn_id,
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
