"""실행부 공통 Tool 이벤트 생성.

Claude·OpenAI 이벤트 어댑터가 같은 `tool_call`/`tool_result`/`status` 형식을 내도록
`AgentEvent` 조립과 Tool 결과 정규화를 이곳에 둔다.
"""

import json
from typing import Any

from api.schemas import AgentEvent


#: SDK 가 Tool 실행 실패로 표시한 결과에는 내부 예외·경로가 들어갈 수 있어 이 문구로 바꾼다.
TOOL_FAILURE_PAYLOAD = {"status": "error", "message": "도구 실행 중 오류가 발생했습니다."}


def coerce_tool_result(content: Any) -> dict[str, Any]:
    """Tool 결과(content)를 Frontend 용 dict 로 정규화한다."""

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


def tool_call_events(tool_name: str, tool_call_id: str, args: dict[str, Any]) -> list[AgentEvent]:
    return [
        AgentEvent(
            type="tool_call",
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            data={"args": args},
        ),
        AgentEvent(
            type="status",
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            data={"step": tool_call_id, "status": "running", "label": f"{tool_name} 실행"},
        ),
    ]


def tool_result_events(tool_name: str, tool_call_id: str, data: dict[str, Any]) -> list[AgentEvent]:
    failed = data.get("status") == "error" or bool(data.get("error"))
    return [
        AgentEvent(
            type="tool_result",
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            data=data,
        ),
        AgentEvent(
            type="status",
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            data={
                "step": tool_call_id,
                "status": "error" if failed else "completed",
                "label": f"{tool_name} {'실패' if failed else '완료'}",
            },
        ),
    ]
