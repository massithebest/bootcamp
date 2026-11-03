"""생산계획 Agent 실행 진입점.

`AGENT_RUNTIME`으로 고른 실행부를 호출할 때 import 한다. 기본 OpenAI 실행부만 쓰는 설치에는
`claude-agent-sdk`가, Claude 실행부만 쓰는 설치에는 `openai-agents`가 없어도 된다.
"""

from collections.abc import AsyncIterator

from api.schemas import AgentEvent
from core import config


async def run_agent(
    message: str,
    conversation_id: str | None = None,
    fork_from_turn_id: str | None = None,
    access_scope: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run the production planning agent.

    Args:
        message:
            User input message.

        conversation_id:
            Frontend conversation identifier.
            It is intentionally separated from an Agent SDK internal
            session identifier.

        fork_from_turn_id:
            편집/재생성 포크 지점 — 이전 `done` 이벤트의 `data.turn_id`.
            `None` 이면 평범한 다음 턴, 빈 문자열이면 처음부터 새로 시작,
            알 수 없는 값이면 `error` 이벤트를 하나 내보내고 새로 시작한다.

        access_scope:
            요청 브라우저 세션의 불투명 scope(차트 v2 §6.1). `execute_sql`/
            `run_simulation`이 저장하는 결과의 접근 범위를 구분하는 데만
            쓰이고, 모델의 tool 입력으로는 노출하지 않는다.

    Yields:
        AgentEvent:
            Frontend-independent common agent events.

    Notes:
        - 실행부 원본 이벤트는 각 실행부가 AgentEvent 로 변환한다.
        - SSE serialization must not be handled in this layer.
        - Internal chain-of-thought must never be exposed.
    """

    if config.AGENT_RUNTIME == "openai":
        from agent.openai_runtime import run_openai_agent as run_runtime
    else:
        from agent.claude_runtime import run_claude_agent as run_runtime

    async for event in run_runtime(message, conversation_id, fork_from_turn_id, access_scope):
        yield event
