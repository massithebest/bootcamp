import type { AgentEvent } from "@/types/chat";

/** SSE 프레임 사이에서 유지되는 파서 상태. */
export class SseParser {
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

/** 공개 envelope만 허용한다. tool별 data 검증은 각 소비자의 책임이다. */
export function parseAgentEvent(payload: string): AgentEvent {
  const value: unknown = JSON.parse(payload);
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Invalid AgentEvent");
  }
  const event = value as Record<string, unknown>;
  const type = event.type;
  if (type !== "text" && type !== "status" && type !== "tool_call" &&
      type !== "tool_result" && type !== "error" && type !== "done") {
    throw new Error("Invalid AgentEvent type");
  }
  if ((event.content != null && typeof event.content !== "string") ||
      (event.tool_name != null && typeof event.tool_name !== "string") ||
      (event.tool_call_id != null && typeof event.tool_call_id !== "string") ||
      (event.data != null && (typeof event.data !== "object" || Array.isArray(event.data)))) {
    throw new Error("Invalid AgentEvent fields");
  }
  return value as AgentEvent;
}
