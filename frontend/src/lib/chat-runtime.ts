/**
 * `ChatMessage` (우리 상태) -> `ThreadMessageLike` (assistant-ui) 어댑터.
 *
 * 메시지 상태의 소유권은 계속 `chat-window.tsx` 가 갖는다. assistant-ui 는
 * `useExternalStoreRuntime` 으로 이 변환 결과만 읽는다.
 *
 * 설계 결정은 docs/decisions.md 참고:
 *   - `parts` 는 도착 순서 배열이고 `content` 도 배열이라 인덱스 대 인덱스로
 *     그대로 옮긴다. 도구 호출 전 내레이션과 최종 답변이 뭉개지지 않는 건
 *     이 순서가 보장한다.
 *   - `statuses`(진행 블록)는 content part 가 아니라 `metadata.custom` 으로
 *     보낸다. 표준 part 유니온에 대응물이 없고, 진행 블록은 답변 본문이
 *     아니라 메시지 머리말이기 때문.
 *   - `tool_call` 만 오고 `tool_result` 가 아직 안 온 중간 상태는 part 를
 *     만들지 않는다. `AgentEvent` 에 tool_call_id 가 없어 병렬 호출을
 *     짝지을 수 없다. 실행 중 표시는 진행 블록이 담당한다.
 */

import type { ThreadMessageLike } from "@assistant-ui/react";

import type { ChatMessage, StatusStep, ToolResult } from "@/types/chat";

/** 어시스턴트 메시지의 `metadata.custom` 에 싣는 값. */
export interface AgentMessageMetadata {
  statuses: StatusStep[];
  streaming: boolean;
  error?: string | null;
}

/** `metadata.custom` 을 우리 타입으로 좁힌다. 형태가 다르면 null. */
export function readAgentMetadata(
  custom: Record<string, unknown> | undefined,
): AgentMessageMetadata | null {
  if (!custom || !Array.isArray(custom.statuses)) return null;
  return {
    statuses: custom.statuses as StatusStep[],
    streaming: custom.streaming === true,
    error: typeof custom.error === "string" ? custom.error : null,
  };
}

/** `tool-result-card.tsx` 의 판정식과 같게 유지한다. */
function isErrorResult(result: ToolResult): boolean {
  const data = result.data;
  if (!data) return false;
  return Boolean(data.error) || data.status === "error";
}

export function convertMessage(message: ChatMessage): ThreadMessageLike {
  if (message.role === "user") {
    return {
      role: "user",
      id: message.id,
      content: [{ type: "text", text: message.content }],
    };
  }

  return {
    role: "assistant",
    id: message.id,
    // 도착 순서 그대로. args/argsText 는 백엔드가 툴 인자를 보내지 않으므로 생략한다.
    content: message.parts.map((part) =>
      part.kind === "text"
        ? { type: "text" as const, text: part.text }
        : {
            type: "tool-call" as const,
            toolCallId: part.id,
            toolName: part.result.toolName,
            // ToolResult 를 통째로 싣는다. ToolResultCard 의 props 를 바꾸지 않기 위함.
            result: part.result,
            isError: isErrorResult(part.result),
          },
    ),
    status: message.streaming
      ? { type: "running" }
      : { type: "complete", reason: "stop" },
    metadata: {
      custom: {
        statuses: message.statuses,
        streaming: message.streaming,
        error: message.error ?? null,
      } satisfies AgentMessageMetadata,
    },
  };
}
