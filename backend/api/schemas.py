"""Frontend / Backend API contracts."""

from typing import Any, Literal

from pydantic import BaseModel


AgentEventType = Literal[
    "text",
    "status",
    "tool_call",
    "tool_result",
    "error",
    "done",
]


class ChatRequest(BaseModel):
    """Chat request from frontend."""

    message: str
    conversation_id: str | None = None
    #: 편집/재생성 포크 지점. `AgentEvent(type="done").data.turn_id` 로 받은 값을
    #: 그대로 돌려준다. 빈 문자열이면 이 대화를 처음부터 다시 시작한다(직전 turn
    #: 이 없거나 turn_id 가 없는 메시지를 편집/재생성할 때). `None`(생략)이면
    #: 평범한 다음 턴 — 대화의 현재 세션을 이어서 실행한다.
    fork_from_turn_id: str | None = None


class AgentEvent(BaseModel):
    """Common agent event exposed to the frontend.

    Frontend rendering behavior is determined by `type`.

    Claude Agent SDK internal message/event types must not be exposed
    directly through this schema.
    """

    type: AgentEventType
    content: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    data: dict[str, Any] | None = None


class VisualizationWarningSchema(BaseModel):
    code: str
    message: str


class VisualizationSeriesSchema(BaseModel):
    key: str
    label: str


class VisualizationChartSchema(BaseModel):
    type: Literal["bar", "line"]
    x: str
    series: list[VisualizationSeriesSchema]
    categories: list[str | int | float]
    data: list[dict[str, Any]]
    title: str | None
    x_label: str | None
    y_label: str | None
    unit: str | None


class VisualizationResponse(BaseModel):
    visualization_id: str
    result_id: str
    schema_version: Literal[1]
    expires_at: str
    chart: VisualizationChartSchema
    warnings: list[VisualizationWarningSchema]
