/**
 * `ChatMessage` (우리 상태) -> `ThreadMessageLike` (assistant-ui) 어댑터.
 *
 * 메시지 상태의 소유권은 계속 `hooks/use-agent-chat.ts` 가 갖는다. assistant-ui 는
 * `useExternalStoreRuntime` 으로 이 변환 결과만 읽는다.
 *
 * 일반 Tool part는 실행 과정으로 앞에 모은다. 그 뒤의 설명과 standalone 표·차트는
 * AgentEvent에서 발생한 순서를 보존해 각 Tool UI와 해석을 같은 문맥에 표시한다.
 * assistant-ui GroupedParts는 일반 Tool만 하나의 ToolGroup으로 표현한다.
 */

import type { MessageStatus, ThreadMessageLike } from "@assistant-ui/react";
import type { ReadonlyJSONObject } from "assistant-stream/utils";

import type {
  ChatMessage,
  ChatMessageRunState,
  MessagePart,
  StatusStep,
} from "@/types/chat";
import { visualizationIdFromToolResult } from "./chart-marker";
import { tablePayloadFromToolResult } from "./table-tool";
import { toolResultError } from "./tool-result";

const STANDALONE_TOOL_NAMES = new Set(["prepare_table", "prepare_visualization"]);

const MARKDOWN_TABLE_DELIMITER =
  /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/;

/** 성공한 표 Tool UI와 함께 온 GFM 표만 제거해 같은 데이터를 두 번 표시하지 않는다. */
export function removeMarkdownTables(text: string): string {
  const lines = text.split("\n");
  const kept: string[] = [];
  let fence: { marker: string; length: number } | null = null;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const fenceMatch = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
    if (fence) {
      kept.push(line);
      if (fenceMatch && fenceMatch[1][0] === fence.marker &&
          fenceMatch[1].length >= fence.length && !fenceMatch[2].trim()) fence = null;
      continue;
    }
    if (fenceMatch) {
      fence = { marker: fenceMatch[1][0], length: fenceMatch[1].length };
      kept.push(line);
      continue;
    }
    const nextLine = lines[index + 1];
    if (lines[index].includes("|") && nextLine && MARKDOWN_TABLE_DELIMITER.test(nextLine)) {
      index += 2;
      while (index < lines.length && lines[index].includes("|")) {
        index += 1;
      }
      index -= 1;
      continue;
    }
    kept.push(lines[index]);
  }

  return kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

export interface AgentMessageMetadata {
  /** Tool 호출과 별개로 Backend가 공개한 사용자용 업무 진행 단계. */
  statuses: StatusStep[];
}

export function readAgentMetadata(
  custom: Record<string, unknown> | undefined,
): AgentMessageMetadata | undefined {
  if (!custom || !Array.isArray(custom.statuses)) return undefined;
  return { statuses: custom.statuses as StatusStep[] };
}

function toAssistantStatus(runState: ChatMessageRunState): MessageStatus {
  switch (runState.type) {
    case "running":
      return { type: "running" };
    case "complete":
      return { type: "complete", reason: "stop" };
    case "cancelled":
      return { type: "incomplete", reason: "cancelled" };
    case "error":
      return {
        type: "incomplete",
        reason: "error",
        error: runState.message,
      };
  }
}

export function convertMessage(message: ChatMessage): ThreadMessageLike {
  if (message.role === "user") {
    return {
      role: "user",
      id: message.id,
      content: [{ type: "text", text: message.content }],
    };
  }

  const toolParts = message.parts.filter(
    (part): part is Extract<MessagePart, { kind: "tool" }> =>
      part.kind === "tool" && !STANDALONE_TOOL_NAMES.has(part.toolName),
  );
  const allStandaloneParts = message.parts.filter(
    (part): part is Extract<MessagePart, { kind: "tool" }> =>
      part.kind === "tool" && STANDALONE_TOOL_NAMES.has(part.toolName),
  );
  const standaloneParts = allStandaloneParts.filter((part, index) =>
    shouldShowStandalonePart(part, index, allStandaloneParts),
  );
  // 일반 Tool 사이의 준비 문구는 숨기되, 이미 제시한 표·차트가 있는 문맥은
  // 이후 추가 조회가 있어도 보존한다. 마지막 구간은 일반 텍스트 답변도 유지한다.
  const responseParts: MessagePart[] = [];
  let segment: MessagePart[] = [];
  for (const part of message.parts) {
    if (part.kind === "tool" && !STANDALONE_TOOL_NAMES.has(part.toolName)) {
      if (segment.some((item) => item.kind === "tool")) responseParts.push(...segment);
      segment = [];
    } else {
      segment.push(part);
    }
  }
  responseParts.push(...segment);
  const hasSuccessfulTable = standaloneParts.some(
    (part) =>
      part.toolName === "prepare_table" && tablePayloadFromToolResult(part.result) !== null,
  );
  const visibleStandaloneIds = new Set(standaloneParts.map((part) => part.toolCallId));
  const contextualParts: MessagePart[] = [];
  for (const part of responseParts) {
    if (part.kind === "tool") {
      if (STANDALONE_TOOL_NAMES.has(part.toolName) && visibleStandaloneIds.has(part.toolCallId)) {
        contextualParts.push(part);
      }
      continue;
    }
    const text = hasSuccessfulTable ? removeMarkdownTables(part.text) : part.text;
    if (text.length > 0) contextualParts.push({ ...part, text });
  }
  const visibleParts = [...toolParts, ...contextualParts];
  // Tool에 연결된 status는 Tool part가 직접 표현한다. metadata에는 독립적인
  // 공개 진행 단계만 전달해 ToolGroup 안에서 중복 없이 함께 렌더링한다.
  const independentStatuses = message.statuses.filter(
    (step) => !step.toolCallId && !step.toolName,
  );

  return {
    role: "assistant",
    id: message.id,
    // 일반 Tool은 실행 과정 그룹으로 앞에 모으고, 표·차트가 있는 문맥과
    // 마지막 답변 구간은 원래 순서대로 배치한다.
    content: visibleParts.map((part) =>
      part.kind === "text"
        ? { type: "text" as const, text: part.text }
        : (() => {
            const status = message.statuses.find(
              (step) => step.toolCallId === part.toolCallId || step.step === part.toolCallId,
            );
            // AgentEvent payload is parsed JSON; narrow it to assistant-ui's JSON type.
            const args = (part.args ?? status?.args ?? {}) as ReadonlyJSONObject;
            return {
              type: "tool-call" as const,
              toolCallId: part.toolCallId,
              toolName: part.toolName,
              args,
              argsText: JSON.stringify(args),
              ...(part.result
                ? {
                    result: part.result,
                    isError: toolResultError(part.result) !== null,
                  }
                : {}),
            };
          })(),
    ),
    status: toAssistantStatus(message.runState),
    metadata: {
      custom: {
        statuses: independentStatuses,
      },
    },
  };
}

/** 같은 Tool/result_id의 후속 성공으로 보정된 실패 호출은 standalone UI에서 숨긴다. */
function shouldShowStandalonePart(
  part: Extract<MessagePart, { kind: "tool" }>,
  index: number,
  parts: Extract<MessagePart, { kind: "tool" }>[],
): boolean {
  if (isSuccessfulStandalonePart(part)) return true;
  const resultId = typeof part.args?.result_id === "string" ? part.args.result_id : null;
  if (!resultId) return true;
  return !parts.slice(index + 1).some(
    (later) =>
      later.toolName === part.toolName &&
      later.args?.result_id === resultId &&
      isSuccessfulStandalonePart(later),
  );
}

function isSuccessfulStandalonePart(
  part: Extract<MessagePart, { kind: "tool" }>,
): boolean {
  if (part.toolName === "prepare_visualization") {
    return visualizationIdFromToolResult(part.result) !== null;
  }
  if (part.toolName === "prepare_table") {
    return tablePayloadFromToolResult(part.result) !== null;
  }
  return false;
}
