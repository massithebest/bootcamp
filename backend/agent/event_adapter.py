"""Convert Claude Agent SDK events into common AgentEvent objects."""

import json
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from api.schemas import AgentEvent
from agent.sdk_tools import MCP_SERVER_NAME


_MCP_PREFIX = f"mcp__{MCP_SERVER_NAME}__"


def _is_business_tool(name: str | None) -> bool:
    """생산계획 업무 Tool 인지 여부.

    `Skill`, `Read`, `Bash` 등 SDK 내장 Tool 은 Frontend 계약에서 제외한다.
    """

    return bool(name) and name.startswith(_MCP_PREFIX)


def _short_tool_name(name: str | None) -> str | None:
    """`mcp__planning__execute_sql` -> `execute_sql`.

    Frontend 는 SDK 내부 MCP 네이밍 규칙을 알 필요가 없다.
    """

    if name and name.startswith(_MCP_PREFIX):
        return name[len(_MCP_PREFIX):]
    return name


def _coerce_tool_result(content: Any) -> dict[str, Any]:
    """ToolResultBlock 의 content 를 Frontend 용 dict 로 정규화한다."""

    text: str | None = None

    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        text = "".join(parts) if parts else None

    if text is None:
        return {"raw": content}

    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return {"text": text}

    return parsed if isinstance(parsed, dict) else {"result": parsed}


class AgentEventAdapter:
    """SDK 이벤트 스트림을 `AgentEvent` 스트림으로 변환한다.

    ToolResultBlock 에는 Tool 이름이 없고 `tool_use_id` 만 있으므로,
    Adapter 가 tool_use_id -> tool_name 매핑을 유지한다.

    Notes:
        - 내부 reasoning / chain-of-thought(ThinkingBlock)는 노출하지 않는다.
        - Frontend 에는 업무적으로 의미 있는 text / status / tool_call /
          tool_result 만 전달한다.
    """

    def __init__(self) -> None:
        self._tool_name_by_id: dict[str, str] = {}
        self._last_session_id: str | None = None
        self._last_entry_uuid: str | None = None

    @property
    def session_id(self) -> str | None:
        """가장 최근 SDK 실행 Session id."""

        return self._last_session_id

    @property
    def last_entry_uuid(self) -> str | None:
        """가장 최근에 관측된 Transcript Entry uuid.

        AssistantMessage/UserMessage 만 대상이다. `ResultMessage.uuid` 도
        필드는 있지만 실제 Transcript(JSONL)에는 적히지 않는 프로토콜
        프레임이라 `resume_session_at` 에 넘기면 CLI 가
        "No message found with message.uuid of: ..." 로 거부한다 — 실제
        Claude CLI 로 직접 재현해 확인했다. 이 턴이 끝난 시점의 마지막
        AssistantMessage/UserMessage 값이 편집/재생성의 포크 지점
        (`ClaudeAgentOptions.resume_session_at`)이 된다.
        """

        return self._last_entry_uuid

    def convert(self, raw_event: object) -> list[AgentEvent]:
        """SDK 이벤트 1개를 0개 이상의 `AgentEvent` 로 변환한다."""

        if isinstance(raw_event, (AssistantMessage, UserMessage)):
            uuid = getattr(raw_event, "uuid", None)
            if isinstance(uuid, str):
                self._last_entry_uuid = uuid

        if isinstance(raw_event, AssistantMessage):
            return self._convert_assistant(raw_event)

        if isinstance(raw_event, UserMessage):
            return self._convert_user(raw_event)

        if isinstance(raw_event, SystemMessage):
            return self._convert_system(raw_event)

        if isinstance(raw_event, ResultMessage):
            self._last_session_id = raw_event.session_id
            if raw_event.is_error:
                return [
                    AgentEvent(
                        type="error",
                        content="Agent 실행이 정상적으로 완료되지 않았습니다.",
                    )
                ]
            return []

        return []

    # -- block level ------------------------------------------------------

    def _convert_assistant(self, message: AssistantMessage) -> list[AgentEvent]:
        events: list[AgentEvent] = []

        for block in message.content:
            if isinstance(block, TextBlock):
                if block.text:
                    events.append(
                        AgentEvent(type="text", content=block.text)
                    )

            elif isinstance(block, ToolUseBlock):
                self._tool_name_by_id[block.id] = block.name
                if not _is_business_tool(block.name):
                    # 내장 Tool(Skill/Read/Bash 등)은 Frontend 로 전달하지 않는다.
                    continue
                short = _short_tool_name(block.name)
                events.append(
                    AgentEvent(type="tool_call", tool_name=short)
                )
                events.append(
                    AgentEvent(
                        type="status",
                        data={
                            "step": short,
                            "status": "running",
                            "label": f"{short} 실행",
                        },
                    )
                )

            elif isinstance(block, ThinkingBlock):
                # 내부 reasoning 은 Frontend 에 전달하지 않는다.
                continue

        return events

    def _convert_user(self, message: UserMessage) -> list[AgentEvent]:
        content = message.content

        if not isinstance(content, list):
            return []

        events: list[AgentEvent] = []

        for block in content:
            if not isinstance(block, ToolResultBlock):
                continue

            raw_name = self._tool_name_by_id.get(block.tool_use_id)
            if not _is_business_tool(raw_name):
                continue

            tool_name = _short_tool_name(raw_name)
            data = _coerce_tool_result(block.content)
            status = "error" if getattr(block, "is_error", False) else "completed"

            events.append(
                AgentEvent(
                    type="tool_result",
                    tool_name=tool_name,
                    data=data,
                )
            )
            events.append(
                AgentEvent(
                    type="status",
                    data={
                        "step": tool_name,
                        "status": status,
                        "label": f"{tool_name} 완료",
                    },
                )
            )

        return events

    def _convert_system(self, message: SystemMessage) -> list[AgentEvent]:
        # 현재는 Frontend 로 전달할 SystemMessage 가 없다.
        # 필요 시 message.subtype 기반으로 status 이벤트를 추가한다.
        return []


def convert_agent_event(
    raw_event: object,
    adapter: AgentEventAdapter | None = None,
) -> list[AgentEvent]:
    """단발성 변환 helper.

    스트림 전체를 변환할 때는 `AgentEventAdapter` 인스턴스를 직접 사용한다.
    (tool_use_id -> tool_name 매핑이 유지되어야 tool_result 이름이 채워진다.)
    """

    return (adapter or AgentEventAdapter()).convert(raw_event)
