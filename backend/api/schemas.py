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


class AgentEvent(BaseModel):
    """Common agent event exposed to the frontend.

    Frontend rendering behavior is determined by `type`.

    Claude Agent SDK internal message/event types must not be exposed
    directly through this schema.
    """

    type: AgentEventType
    content: str | None = None
    tool_name: str | None = None
    data: dict[str, Any] | None = None
