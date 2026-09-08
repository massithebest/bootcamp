/**
 * Backend `api/schemas.py` 의 AgentEvent 와 동일한 Contract 를 유지한다.
 *
 * Backend AgentEvent:
 *   type: "text" | "status" | "tool_call" | "tool_result" | "error" | "done"
 *   content?: string
 *   tool_name?: string
 *   data?: Record<string, unknown>
 *
 * Claude Agent SDK 내부 Event 는 절대 이 타입으로 노출되지 않는다.
 */

export type AgentEventType =
  | "text"
  | "status"
  | "tool_call"
  | "tool_result"
  | "error"
  | "done";

export interface AgentEvent {
  type: AgentEventType;
  content?: string | null;
  tool_name?: string | null;
  data?: Record<string, unknown> | null;
}

/** status Event 의 진행 상태 값. */
export type StepStatus = "pending" | "running" | "completed" | "error";

/**
 * Assistant Message 안에서 관리하는 단일 진행 단계.
 * Backend status Event 는 보통 다음 형태의 data 를 전달한다:
 *   { step: string, label?: string, status: StepStatus }
 */
export interface StatusStep {
  /** 같은 step 에 대한 Event 가 오면 기존 항목을 갱신한다. */
  step: string;
  label: string;
  status: StepStatus;
}

/** tool_result Event 로부터 만들어지는 Tool 결과 항목. */
export interface ToolResult {
  id: string;
  toolName: string;
  /** Backend data 를 그대로 보관한다. tool_name 별 전용 UI 확장 지점. */
  data: Record<string, unknown> | null;
  /** data 가 없을 때의 텍스트 결과. */
  content?: string | null;
}

/**
 * Assistant 응답을 도착 순서대로 담는 조각.
 * text delta 와 tool 결과가 시간순으로 섞여 들어오므로,
 * 하나의 content 문자열로 뭉치지 않고 조각 목록으로 관리한다.
 * (도구 실행 전 서술과 최종 답변이 한 덩어리로 붙는 문제를 방지)
 */
export type MessagePart =
  | { kind: "text"; id: string; text: string }
  | { kind: "tool"; id: string; result: ToolResult };

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  /** 사용자 메시지 본문. assistant 메시지에서는 사용하지 않는다. */
  content: string;
  /** Assistant 응답 조각(텍스트 / 도구 결과) — 도착 순서. */
  parts: MessagePart[];
  /** Assistant 진행 상태(접이식 진행 블록). */
  statuses: StatusStep[];
  /** 이 message 가 아직 streaming 중인지. */
  streaming: boolean;
  /** 사용자에게 보여줄 오류 메시지. */
  error?: string | null;
}

export interface ChatRequestBody {
  message: string;
  conversation_id?: string;
}
