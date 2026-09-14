"""Claude Agent SDK initialization and execution."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from agent.event_adapter import AgentEventAdapter
from agent.fake_runner import run_fake_agent
from agent.sdk_tools import TOOL_NAMES, build_planning_mcp_server
from agent.session_store import bind_session_id, get_session_id
from agent.system_prompt import SYSTEM_PROMPT
from api.schemas import AgentEvent
from core.config import AGENT_MODEL, CLAUDE_CLI_PATH, agent_provider_env


#: `agent/agent_sdk/` — CLAUDE.md 와 .claude/skills 가 위치한 Agent 작업 디렉터리.
AGENT_SDK_CWD = str((Path(__file__).parent / "agent_sdk").resolve())

def _use_fake_runner() -> bool:
    """네트워크 없이 전체 이벤트 흐름을 검증할지 여부. (테스트 / 데모)"""

    return os.getenv("PLANNING_AGENT_FAKE", "").lower() in {"1", "true", "yes"}


def _build_options(resume_session_id: str | None) -> ClaudeAgentOptions:
    """Claude Agent SDK 실행 옵션을 구성한다."""

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=AGENT_SDK_CWD,
        setting_sources=["project"],  # CLAUDE.md / .claude/skills 로드
        mcp_servers={"planning": build_planning_mcp_server()},
        # Skill: 프로젝트 Skills(.claude/skills/*)를 에이전트가 선택해 로드한다.
        # 문자열 system_prompt 로도 Claude Code preset 의 Skill 도구가 유지된다 (Task 0 확인).
        allowed_tools=TOOL_NAMES + ["Skill"],
        permission_mode="bypassPermissions",
        resume=resume_session_id,
        model=AGENT_MODEL,
        # LLM_PROVIDER=openrouter 이면 base URL / 토큰을 주입한다. (기본: {})
        env=agent_provider_env() or None,
        # PATH 에 `claude` 가 없어도 실행되도록 경로를 명시한다. (없으면 SDK 자체 탐색)
        cli_path=CLAUDE_CLI_PATH,
    )


async def run_agent(
    message: str,
    conversation_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """Run the production planning agent.

    Args:
        message:
            User input message.

        conversation_id:
            Frontend conversation identifier.
            It is intentionally separated from an Agent SDK internal
            session identifier.

    Yields:
        AgentEvent:
            Frontend-independent common agent events.

    Notes:
        - Claude Agent SDK original events must be converted into AgentEvent.
        - SSE serialization must not be handled in this layer.
        - Internal chain-of-thought must never be exposed.
    """

    if _use_fake_runner():
        async for event in run_fake_agent(message, conversation_id):
            yield event
        return

    adapter = AgentEventAdapter()
    resume_session_id = get_session_id(conversation_id)
    options = _build_options(resume_session_id)

    try:
        async for raw_event in query(prompt=message, options=options):
            for event in adapter.convert(raw_event):
                yield event
    finally:
        # SDK session_id 를 사용자 대화에 연결해 후속 turn 에서 이어서 실행한다.
        bind_session_id(conversation_id, adapter.session_id)

    yield AgentEvent(type="done")
