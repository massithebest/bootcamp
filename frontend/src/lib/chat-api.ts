/**
 * Backend 와의 통신만 담당한다.
 *
 *   POST /api/chat
 *    -> SSE Streaming
 *    -> AgentEvent 변환
 *    -> ChatWindow 전달 (onEvent 콜백)
 *
 * Vercel AI SDK (`ai`, `@ai-sdk/react`) 는 현재 프로젝트에 설치되어 있지 않으므로
 * Browser 기본 API (fetch / ReadableStream / TextDecoder / AbortController) 로 구현한다.
 * 외부 SSE Parser Package 는 추가하지 않는다.
 *
 */

import type { AgentEvent, ChatRequestBody } from "@/types/chat";
import { SseParser, parseAgentEvent } from "./chat-sse";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface SendChatMessageOptions {
  message: string;
  conversationId?: string;
  /** 편집/재생성 포크 지점. `ChatRequestBody.fork_from_turn_id` 로 그대로 전달한다. */
  forkFromTurnId?: string;
  /** 각 AgentEvent 를 순서대로 전달받는다. */
  onEvent: (event: AgentEvent) => void;
  /** 현재 요청 취소용. */
  signal?: AbortSignal;
}

/**
 * `/api/chat` 를 호출하고 SSE 로 들어오는 AgentEvent 를 onEvent 로 전달한다.
 *
 * 오류는 throw 하지 않고 `error` / `done` AgentEvent 로 정규화하여 전달한다.
 * 반환값은 transport 종료 결과다. Backend error 이벤트와 연결 실패를 구분한다.
 */
export async function sendChatMessage(
  options: SendChatMessageOptions,
): Promise<"complete" | "failed" | "aborted"> {
  const { message, conversationId, forkFromTurnId, onEvent, signal } = options;

  const body: ChatRequestBody = { message };
  if (conversationId) body.conversation_id = conversationId;
  if (forkFromTurnId !== undefined) body.fork_from_turn_id = forkFromTurnId;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
      signal,
      credentials: "include",
    });
  } catch (err) {
    if (signal?.aborted || isAbortError(err)) return "aborted";
    console.error("[chat-api] Backend 연결 실패");
    onEvent({ type: "error", content: "Backend 에 연결하지 못했습니다." });
    onEvent({ type: "done" });
    return "failed";
  }

  if (signal?.aborted) return "aborted";

  if (!response.ok) {
    console.error("[chat-api] HTTP 오류", response.status);
    onEvent({
      type: "error",
      content: `요청을 처리하지 못했습니다. (HTTP ${response.status})`,
    });
    onEvent({ type: "done" });
    return "failed";
  }

  if (!response.body) {
    onEvent({ type: "error", content: "응답 스트림을 읽을 수 없습니다." });
    onEvent({ type: "done" });
    return "failed";
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  let sawDone = false;
  let transportFailed = false;

  const emit = (payload: string) => {
    if (sawDone || signal?.aborted) return;
    const event = parseAgentEvent(payload);
    if (event.type === "done") sawDone = true;
    onEvent(event);
  };

  try {
    while (!sawDone && !signal?.aborted) {
      const { value, done } = await reader.read();
      if (signal?.aborted) return "aborted";
      for (const payload of parser.push(
        done ? decoder.decode() : decoder.decode(value, { stream: true }),
      )) emit(payload);
      if (done) break;
    }
    if (!sawDone && !signal?.aborted) {
      transportFailed = true;
      onEvent({ type: "error", content: "응답이 완료되기 전에 연결이 종료되었습니다." });
    }
  } catch (err) {
    if (signal?.aborted || isAbortError(err)) return "aborted";
    transportFailed = true;
    // malformed payload/SDK 원문을 콘솔이나 사용자 오류에 싣지 않는다.
    onEvent({ type: "error", content: "응답을 받는 중 오류가 발생했습니다." });
  } finally {
    // done 이후 서버가 연결을 열어 두어도 요청과 reader를 남기지 않는다.
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }

  if (signal?.aborted) return "aborted";
  if (!sawDone) onEvent({ type: "done" });
  return transportFailed ? "failed" : "complete";
}

function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

/** POC 용 client-side conversation id. 향후 Backend Memory/History 와 연결. */
export function createConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
