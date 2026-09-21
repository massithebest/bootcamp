"""Claude Agent SDK initialization and execution."""

import re
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from agent.event_adapter import AgentEventAdapter
from agent.sdk_tools import TOOL_NAMES, build_planning_mcp_server
from agent.session_store import (
    bind_session_id,
    get_session_id,
    get_turn_anchor,
    record_turn_anchor,
)
from agent.system_prompt import SYSTEM_PROMPT
from api.schemas import AgentEvent
from core.config import AGENT_MODEL, CLAUDE_CLI_PATH, agent_provider_env
from tools.table_tool import prepare_table


#: `agent/agent_sdk/` — CLAUDE.md 와 .claude/skills 가 위치한 Agent 작업 디렉터리.
AGENT_SDK_CWD = str((Path(__file__).parent / "agent_sdk").resolve())

# '목표', '지표', '대표', 'stable'은 명시적인 표 요청이 아니다.
_TABLE_REQUEST_PATTERN = re.compile(
    r"(?<![\w])(?:표|테이블)(?=$|[^\w]|로|으로|를|을|에|의|만|도|가|는|은|형태|형식)"
    r"|(?<![\w])tables?(?![a-zA-Z_])",
    re.IGNORECASE,
)
_MARKDOWN_TABLE_DELIMITER = re.compile(
    r"(?m)^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
_TABLE_SOURCE_TOOLS = {
    "execute_sql",
    "run_simulation",
    "get_result_page",
    "get_result_summary",
}


def _needs_table_fallback(message: str, response_text: str) -> bool:
    """명시적인 표 요청 또는 Markdown 표 응답이면 Tool UI 보완이 필요하다."""

    return bool(
        _TABLE_REQUEST_PATTERN.search(message)
        or _MARKDOWN_TABLE_DELIMITER.search(response_text)
    )


async def _table_fallback_events(
    result_id: str,
    *,
    access_scope: str | None,
) -> list[AgentEvent]:
    """모델이 빠뜨린 prepare_table 호출을 공개 AgentEvent로 보완한다."""

    tool_call_id = f"auto-prepare-table-{uuid.uuid4().hex}"
    args = {"result_id": result_id}
    result = await prepare_table(result_id=result_id, access_scope=access_scope)
    failed = result.get("status") == "error"
    return [
        AgentEvent(
            type="tool_call",
            tool_name="prepare_table",
            tool_call_id=tool_call_id,
            data={"args": args},
        ),
        AgentEvent(
            type="status",
            tool_name="prepare_table",
            tool_call_id=tool_call_id,
            data={
                "step": tool_call_id,
                "status": "running",
                "label": "대화형 표 준비",
            },
        ),
        AgentEvent(
            type="tool_result",
            tool_name="prepare_table",
            tool_call_id=tool_call_id,
            data=result,
        ),
        AgentEvent(
            type="status",
            tool_name="prepare_table",
            tool_call_id=tool_call_id,
            data={
                "step": tool_call_id,
                "status": "error" if failed else "completed",
                "label": "대화형 표 준비 실패" if failed else "대화형 표 준비 완료",
            },
        ),
    ]


def _build_options(
    resume_session_id: str | None,
    resume_session_at: str | None = None,
    access_scope: str | None = None,
) -> ClaudeAgentOptions:
    """Claude Agent SDK 실행 옵션을 구성한다.

    `resume_session_at` 이 주어지면(편집/재생성 포크) `fork_session=True` 로
    새 session_id 를 받는다 — 원본 session 파일을 그 자리에서 잘라내지 않고
    그 지점까지만 복사해 새 세션으로 이어간다. 평범한 다음 턴(`resume_session_at`
    없음)은 지금까지와 동일하게 같은 session_id 에 계속 이어 쓴다.

    `access_scope`는 요청 브라우저 세션의 불투명 scope다(차트 v2 §6.1) —
    Result Store 접근 범위 구분에만 쓰이고 모델 입력으로 노출되지 않는다.
    """

    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=AGENT_SDK_CWD,
        setting_sources=["project"],  # CLAUDE.md / .claude/skills 로드
        mcp_servers={"planning": build_planning_mcp_server(access_scope)},
        # Skill: 프로젝트 Skills(.claude/skills/*)를 에이전트가 선택해 로드한다.
        # 문자열 system_prompt 로도 Claude Code preset 의 Skill 도구가 유지된다 (Task 0 확인).
        allowed_tools=TOOL_NAMES + ["Skill"],
        permission_mode="bypassPermissions",
        resume=resume_session_id,
        fork_session=resume_session_at is not None,
        resume_session_at=resume_session_at,
        model=AGENT_MODEL,
        # LLM_PROVIDER=openrouter 이면 base URL / 토큰을 주입한다. (기본: {})
        env=agent_provider_env() or None,
        # PATH 에 `claude` 가 없어도 실행되도록 경로를 명시한다. (없으면 SDK 자체 탐색)
        cli_path=CLAUDE_CLI_PATH,
        # SDK의 최종 AssistantMessage를 기다리지 않고 text_delta를 받아
        # 기존 AgentEvent text/SSE 경로로 전달한다. Adapter가 provider
        # message id를 기준으로 최종 누적 TextBlock의 중복 전송을 막는다.
        include_partial_messages=True,
    )


def _resolve_resume(
    conversation_id: str | None,
    fork_from_turn_id: str | None,
) -> tuple[str | None, str | None, AgentEvent | None]:
    """`resume`/`resume_session_at` 에 넘길 값을 계산한다.

    Returns:
        (resume_session_id, resume_session_at, warning_event).
        `warning_event` 는 알 수 없는 turn_id 로 새 대화로 폴백했을 때만 채워진다.
    """

    if fork_from_turn_id is None:
        # 평범한 다음 턴 — 대화의 현재 세션을 이어서 실행한다. (기존 동작)
        return get_session_id(conversation_id), None, None

    if fork_from_turn_id == "":
        # 이 대화를 처음부터 다시 시작한다 (직전 turn 이 없거나, turn_id 가
        # 없는 메시지 — 예: 더미 시드 대화 — 를 편집/재생성할 때).
        return None, None, None

    anchor = get_turn_anchor(fork_from_turn_id)
    if anchor is None:
        warning = AgentEvent(
            type="error",
            content="이전 응답 지점을 찾을 수 없어 새 대화로 시작합니다.",
        )
        return None, None, warning

    return anchor.session_id, anchor.last_entry_uuid, None


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
        - Claude Agent SDK original events must be converted into AgentEvent.
        - SSE serialization must not be handled in this layer.
        - Internal chain-of-thought must never be exposed.
    """

    turn_id = str(uuid.uuid4())
    resume_session_id, resume_session_at, warning = _resolve_resume(
        conversation_id, fork_from_turn_id
    )
    if warning is not None:
        yield warning

    adapter = AgentEventAdapter()
    options = _build_options(resume_session_id, resume_session_at, access_scope)
    response_text: list[str] = []
    last_result_id: str | None = None
    table_prepared = False

    async for raw_event in query(prompt=message, options=options):
        for event in adapter.convert(raw_event):
            if event.type == "text" and event.content:
                response_text.append(event.content)
            if event.type == "tool_result" and isinstance(event.data, dict):
                if (
                    event.tool_name in _TABLE_SOURCE_TOOLS
                    and event.data.get("status") == "ok"
                    and isinstance(event.data.get("result_id"), str)
                ):
                    last_result_id = event.data["result_id"]
                if (
                    event.tool_name == "prepare_table"
                    and event.data.get("status") == "ok"
                ):
                    table_prepared = True
            yield event

    # 예외/취소 cleanup에서는 완료 세션을 덮어쓰지 않는다. SDK 결과가 없이
    # 닫힌 경우도 성공 turn으로 기록하지 않는다.
    if adapter.result_succeeded is not True:
        if adapter.result_succeeded is None:
            yield AgentEvent(type="error", content="Agent 응답이 완료되기 전에 종료되었습니다.")
        yield AgentEvent(type="done")
        return

    if (
        last_result_id is not None
        and not table_prepared
        and _needs_table_fallback(message, "".join(response_text))
    ):
        for event in await _table_fallback_events(
            last_result_id,
            access_scope=access_scope,
        ):
            yield event

    bind_session_id(conversation_id, adapter.session_id)
    if adapter.session_id:
        record_turn_anchor(turn_id, adapter.session_id, adapter.last_entry_uuid)

    yield AgentEvent(type="done", data={"turn_id": turn_id})
