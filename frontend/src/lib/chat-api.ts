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
 * AI SDK 가 추가되더라도 이 모듈의 함수 시그니처( sendChatMessage )는 유지하고
 * 내부 구현만 Transport 로 교체한다. Component 는 영향받지 않는다.
 */

import type { AgentEvent, ChatRequestBody } from "@/types/chat";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface SendChatMessageOptions {
  message: string;
  conversationId?: string;
  /** 각 AgentEvent 를 순서대로 전달받는다. */
  onEvent: (event: AgentEvent) => void;
  /** Streaming 취소용. 초기 UI 에 Stop 버튼이 없어도 구조는 유지한다. */
  signal?: AbortSignal;
}

/** SSE 프레임 사이에서 유지되는 파서 상태. */
class SseParser {
  private buffer = "";

  /** 새 chunk 를 받아 완성된 data payload 문자열들을 반환한다. */
  push(chunk: string): string[] {
    this.buffer += chunk;
    const payloads: string[] = [];

    // SSE Event 경계는 빈 줄(\n\n). \r\n 도 방어적으로 처리한다.
    let boundary: number;
    while ((boundary = this.indexOfBoundary()) !== -1) {
      const rawEvent = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(this.boundaryEnd(boundary));

      const data = this.extractData(rawEvent);
      if (data !== null) payloads.push(data);
    }
    return payloads;
  }

  /** stream 종료 시 buffer 에 남은 마지막 Event 를 처리한다. */
  flush(): string[] {
    const remaining = this.buffer.trim();
    this.buffer = "";
    if (!remaining) return [];
    const data = this.extractData(remaining);
    return data !== null ? [data] : [];
  }

  private indexOfBoundary(): number {
    const lf = this.buffer.indexOf("\n\n");
    const crlf = this.buffer.indexOf("\r\n\r\n");
    if (lf === -1) return crlf;
    if (crlf === -1) return lf;
    return Math.min(lf, crlf);
  }

  private boundaryEnd(index: number): number {
    return this.buffer.startsWith("\r\n\r\n", index) ? index + 4 : index + 2;
  }

  /** 하나의 raw SSE Event 블록에서 `data:` 라인들을 이어붙여 반환한다. */
  private extractData(rawEvent: string): string | null {
    const lines = rawEvent.split(/\r?\n/);
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).replace(/^ /, ""));
      }
    }
    if (dataLines.length === 0) return null;
    return dataLines.join("\n");
  }
}

function parseAgentEvent(payload: string): AgentEvent | null {
  const trimmed = payload.trim();
  if (!trimmed || trimmed === "[DONE]") return null;
  try {
    const obj = JSON.parse(trimmed) as AgentEvent;
    if (obj && typeof obj.type === "string") return obj;
    return null;
  } catch {
    console.warn("[chat-api] AgentEvent JSON 파싱 실패", trimmed);
    return null;
  }
}

/**
 * `/api/chat` 를 호출하고 SSE 로 들어오는 AgentEvent 를 onEvent 로 전달한다.
 *
 * 오류는 throw 하지 않고 `error` / `done` AgentEvent 로 정규화하여 전달한다.
 * (Component 는 Event Type 만 처리하면 되도록.)
 */
export async function sendChatMessage(
  options: SendChatMessageOptions,
): Promise<void> {
  const { message, conversationId, onEvent, signal } = options;

  const body: ChatRequestBody = { message };
  if (conversationId) body.conversation_id = conversationId;

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
    });
  } catch (err) {
    if (isAbortError(err)) return;
    console.error("[chat-api] Backend 연결 실패", err);
    onEvent({ type: "error", content: "Backend 에 연결하지 못했습니다." });
    onEvent({ type: "done" });
    return;
  }

  if (!response.ok) {
    console.error("[chat-api] HTTP 오류", response.status);
    onEvent({
      type: "error",
      content: `요청을 처리하지 못했습니다. (HTTP ${response.status})`,
    });
    onEvent({ type: "done" });
    return;
  }

  if (!response.body) {
    onEvent({ type: "error", content: "응답 스트림을 읽을 수 없습니다." });
    onEvent({ type: "done" });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  let sawDone = false;

  const emit = (payload: string) => {
    const event = parseAgentEvent(payload);
    if (!event) return;
    if (event.type === "done") sawDone = true;
    onEvent(event);
  };

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const payload of parser.push(decoder.decode(value, { stream: true }))) {
        emit(payload);
      }
    }
    for (const payload of parser.flush()) emit(payload);
  } catch (err) {
    if (isAbortError(err)) return;
    console.error("[chat-api] SSE 스트림 오류", err);
    onEvent({ type: "error", content: "응답을 받는 중 오류가 발생했습니다." });
  } finally {
    reader.releaseLock();
  }

  // Stream 비정상 종료 방어: done 이 없었다면 강제로 종료 신호를 준다.
  if (!sawDone && !signal?.aborted) {
    onEvent({ type: "done" });
  }
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
