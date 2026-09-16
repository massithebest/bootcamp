"""Frontend / Backend API contracts."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


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


class KnowledgeDocumentInput(BaseModel):
    """Public text authoring fields; no server paths or runtime instructions."""
    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)
    category: str = Field(min_length=1, max_length=100)
    tags: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(default_factory=list, max_length=30)
    owner: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=500)


class KnowledgeDocumentUpdate(KnowledgeDocumentInput):
    expected_revision: int = Field(ge=1)


class KnowledgeActionInput(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    expected_revision: int = Field(ge=1)
    version: int | None = Field(default=None, ge=1)
    actor: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=2000)


class KnowledgeVersion(KnowledgeDocumentInput):
    version: int
    status: Literal["draft", "verified"]
    created_at: str
    reviewer: str
    review_note: str
    reviewed_at: str | None


class KnowledgeHistory(BaseModel):
    revision: int
    action: Literal["save", "review", "activate", "deactivate", "archive"]
    version: int | None
    actor: str
    note: str
    at: str


class KnowledgeDocumentResponse(BaseModel):
    id: str
    revision: int
    active_version: int | None
    archived: bool
    versions: list[KnowledgeVersion]
    history: list[KnowledgeHistory]


class KnowledgeEntryResponse(BaseModel):
    type: Literal["document", "table", "kpi", "recipe", "glossary", "simulation"]
    id: str
    title: str
    summary: str
    status: Literal["draft", "verified"]
    source: str
    owner: str
    updated: str
    active: bool | None
    archived: bool


class KnowledgeEntryDetail(KnowledgeEntryResponse):
    detail: dict[str, Any]


class KnowledgeToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output: str
    status: Literal["available"]
