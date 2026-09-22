"""Frontend / Backend API contracts."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class QueryColumnSchema(BaseModel):
    name: str
    dtype: str
    role: str | None


class QueryPreviewResponse(BaseModel):
    """Bounded metadata only — never the full rows."""

    status: Literal["ok"]
    result_id: str
    row_count: int
    source_truncated: bool
    columns: list[QueryColumnSchema]
    sample_rows: list[dict[str, Any]]
    date_ranges: dict[str, dict[str, Any]]
    distinct_counts: dict[str, int]
    statistics: dict[str, dict[str, Any]]
    top_groups: dict[str, list[dict[str, Any]]]


class QueryTableResponse(BaseModel):
    status: Literal["ok"]
    result_id: str
    page: int
    page_size: int
    row_count: int
    filtered_row_count: int
    source_truncated: bool
    columns: list[QueryColumnSchema]
    rows: list[list[Any]]


class QueryChartSchema(BaseModel):
    type: Literal["bar", "line", "area"]
    x: str
    series: list[VisualizationSeriesSchema]
    categories: list[str | int | float]
    data: list[dict[str, Any]]
    title: str | None
    x_label: str | None
    y_label: str | None
    unit: str | None


class QueryChartResponse(BaseModel):
    status: Literal["ok"]
    result_id: str
    chart: QueryChartSchema
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


class PendingChange(BaseModel):
    id: str
    state: Literal["draft", "submitted", "rejected"]


class KnowledgeEntryResponse(BaseModel):
    type: Literal["document", "table", "kpi", "recipe", "glossary", "simulation", "scenario"]
    id: str
    title: str
    summary: str
    status: Literal["draft", "verified"]
    source: str
    owner: str
    updated: str
    active: bool | None
    archived: bool
    pending_change: PendingChange | None = None


class KnowledgeEntryDetail(KnowledgeEntryResponse):
    detail: dict[str, Any]


class KnowledgeToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output: str
    status: Literal["available"]


# ---- 구조화 지식 변경 요청 ----

KnowledgeKindName = Literal["table", "kpi", "recipe", "simulation", "glossary", "scenario"]
ChangeStateName = Literal["draft", "submitted", "approved", "rejected", "withdrawn"]


class _ContentInput(BaseModel):
    """`yaml`(원문 탭)과 `data`(폼) 중 정확히 하나로 내용을 받는다."""

    model_config = {"extra": "forbid"}

    yaml: str | None = Field(default=None, max_length=200_000)
    data: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _exactly_one_content(self):
        if (self.yaml is None) == (self.data is None):
            raise ValueError("yaml 과 data 중 하나만 보내세요.")
        return self


class KnowledgeValidateInput(_ContentInput):
    kind: KnowledgeKindName
    key: str | None = Field(default=None, max_length=200)


class KnowledgeChangeInput(KnowledgeValidateInput):
    """`key` 가 있으면 기존 항목 수정, 없으면 신규 항목이다."""


class KnowledgeChangeUpdate(_ContentInput):
    expected_revision: int = Field(ge=1)


class KnowledgeChangeAction(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}

    expected_revision: int = Field(ge=1)
    note: str = Field(default="", max_length=2000)


class KnowledgeValidationError(BaseModel):
    path: str
    line: int | None
    message: str


class KnowledgeValidationResponse(BaseModel):
    ok: bool
    #: 입력이 YAML/JSON mapping 으로 읽혔는지. false 면 폼으로 옮길 수 없다.
    parsed: bool
    yaml: str
    data: dict[str, Any]
    key: str
    errors: list[KnowledgeValidationError]


class ChangeAuthor(BaseModel):
    id: str
    name: str


class KnowledgeChangeSummary(BaseModel):
    id: str
    kind: KnowledgeKindName
    key: str
    is_new: bool
    state: ChangeStateName
    revision: int
    author: ChangeAuthor
    created_at: str
    updated_at: str


class KnowledgeChangeHistory(BaseModel):
    revision: int
    action: Literal["create", "save", "submit", "withdraw", "approve", "reject"]
    actor_id: str
    actor_name: str
    note: str
    self_approved: bool
    at: str


class KnowledgeChangeDetail(KnowledgeChangeSummary):
    yaml: str
    data: dict[str, Any]
    current_yaml: str
    history: list[KnowledgeChangeHistory]


class KnowledgeSourceResponse(BaseModel):
    kind: KnowledgeKindName
    key: str
    yaml: str
    data: dict[str, Any]


class StubUser(BaseModel):
    id: str
    name: str


class MeResponse(BaseModel):
    id: str
    name: str
    permissions: list[str]
    mode: Literal["stub", "authenticated"]
    knowledge_management: bool
    allow_self_approval: bool
    stub_users: list[StubUser]
