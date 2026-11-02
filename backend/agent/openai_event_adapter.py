"""Convert OpenAI Agents SDK stream events into common AgentEvent objects.

Claude 어댑터(`agent/event_adapter.py`)와 같은 `AgentEvent` 순서·형식을 낸다.

- 텍스트는 raw response 의 `response.output_text.delta`로만 보낸다. 최종 메시지 item 은
  delta 가 없었을 때만 텍스트로 보낸다(중복 방지).
- 숨김 Tool(`load_skill`·`suggest_follow_ups`)과 reasoning item 은 내보내지 않는다.
  후속질문은 Tool 입력을 검증해 마지막 유효 값만 `suggestions`로 보관한다.
"""

import json
from typing import Any

from agents import (
    ItemHelpers,
    MessageOutputItem,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    ToolCallItem,
    ToolCallOutputItem,
)

from api.schemas import AgentEvent
from agent.tool_events import coerce_tool_result, tool_call_events, tool_result_events
from agent.tool_specs import SUGGESTION_TOOL_NAME, tool_specs
from tools.suggestion_tool import normalize_suggestions


#: 화면 Tool 사용 기록에 내보내는 Tool. 그 밖의 Tool(`load_skill`, 후속질문)은 숨긴다.
VISIBLE_TOOL_NAMES = frozenset(spec.name for spec in tool_specs() if spec.visible)

_TEXT_DELTA = "response.output_text.delta"


def _arguments(raw: Any) -> dict[str, Any]:
    try:
        args = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return args if isinstance(args, dict) else {}


def _call_id(raw_item: Any) -> str | None:
    value = raw_item.get("call_id") if isinstance(raw_item, dict) else getattr(raw_item, "call_id", None)
    return value if isinstance(value, str) and value else None


class OpenAIEventAdapter:
    """`RunResultStreaming.stream_events()`를 `AgentEvent` 스트림으로 변환한다.

    Tool 결과 item 에는 Tool 이름이 없고 `call_id`만 있으므로 call_id -> 이름 매핑을 유지한다.
    """

    def __init__(self) -> None:
        self._tool_name_by_id: dict[str, str] = {}
        self._text_streamed = False
        self._suggestions: list[str] | None = None

    @property
    def suggestions(self) -> list[str] | None:
        """이번 실행에서 마지막으로 검증을 통과한 후속질문. 없으면 None."""

        return self._suggestions

    def convert(self, event: object) -> list[AgentEvent]:
        if isinstance(event, RawResponsesStreamEvent):
            data = event.data
            delta = getattr(data, "delta", None)
            if getattr(data, "type", None) == _TEXT_DELTA and isinstance(delta, str) and delta:
                self._text_streamed = True
                return [AgentEvent(type="text", content=delta)]
            return []

        if not isinstance(event, RunItemStreamEvent):
            return []
        item = event.item
        if isinstance(item, MessageOutputItem):
            streamed, self._text_streamed = self._text_streamed, False
            text = ItemHelpers.text_message_output(item)
            return [] if streamed or not text else [AgentEvent(type="text", content=text)]
        if isinstance(item, ToolCallItem):
            return self._tool_called(item.raw_item)
        if isinstance(item, ToolCallOutputItem):
            return self._tool_output(item)
        # reasoning item(모델 추론)과 그 밖의 item 은 항상 무시한다.
        return []

    def _tool_called(self, raw_item: Any) -> list[AgentEvent]:
        call_id = _call_id(raw_item)
        name = getattr(raw_item, "name", None)
        if call_id is None or not isinstance(name, str):
            return []
        self._tool_name_by_id[call_id] = name
        args = _arguments(getattr(raw_item, "arguments", None))
        if name == SUGGESTION_TOOL_NAME:
            # 후속질문은 Tool trace 가 아니라 성공한 done 에만 싣는다.
            suggestions = normalize_suggestions(args.get("questions"))
            if suggestions is not None:
                self._suggestions = suggestions
            return []
        if name not in VISIBLE_TOOL_NAMES:
            return []
        return tool_call_events(name, call_id, args)

    def _tool_output(self, item: ToolCallOutputItem) -> list[AgentEvent]:
        call_id = _call_id(item.raw_item)
        name = self._tool_name_by_id.get(call_id or "")
        if call_id is None or name not in VISIBLE_TOOL_NAMES:
            return []
        return tool_result_events(name, call_id, coerce_tool_result(item.output))
