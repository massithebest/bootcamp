"""Claude Agent SDK 용 Tool 등록 계층.

`agent/tool_specs.py` 의 실행부 중립 Tool 명세를 Claude Agent SDK 가 인식하는
in-process MCP 서버 Tool 로 감싸는 역할만 담당한다.

- Tool 설명·입력 schema·업무 호출은 여기 두지 않는다. (tool_specs + tools/ 담당)
- SDK 종속 코드(@tool, create_sdk_mcp_server)는 이 모듈과 event_adapter 에 모은다.
"""

import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from agent.tool_specs import ToolSpec, tool_specs


MCP_SERVER_NAME = "planning"


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    """업무 결과 dict 를 SDK Tool 결과 형식으로 변환한다.

    Frontend 에서 표현할 구조화 결과는 JSON 문자열로 담아 전달하고,
    event_adapter 가 다시 dict 로 복원한다.
    """

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False),
            }
        ]
    }


def _sdk_tool(spec: ToolSpec, access_scope: str | None):
    async def _handler(args: dict[str, Any]) -> dict[str, Any]:
        return _ok(await spec.handler(args, access_scope))

    return tool(spec.name, spec.description, spec.input_schema)(_handler)


def planning_tools(access_scope: str | None = None):
    """공통 Tool 명세를 `access_scope`에 묶은 Claude SDK Tool 목록."""

    return [_sdk_tool(spec, access_scope) for spec in tool_specs()]


def tool_names() -> list[str]:
    return [f"mcp__{MCP_SERVER_NAME}__{spec.name}" for spec in tool_specs()]


TOOL_NAMES = tool_names()


def build_planning_mcp_server(access_scope: str | None = None):
    return create_sdk_mcp_server(
        name=MCP_SERVER_NAME, version="0.1.0", tools=planning_tools(access_scope),
    )
