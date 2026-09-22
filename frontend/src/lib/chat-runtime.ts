/**
 * `ChatMessage` (우리 상태) -> `ThreadMessageLike` (assistant-ui) 어댑터.
 *
 * 메시지 저장·스트리밍 표시는 assistant-ui LocalRuntime이 맡고, `lib/chat-model-adapter.ts`가
 * 이 변환 결과를 `ChatModelAdapter`의 yield로 넘긴다.
 *
 * 일반 Tool part는 실행 과정으로 앞에 모은다. 그 뒤의 설명과 standalone 표·차트는
 * AgentEvent에서 발생한 순서를 보존해 각 Tool UI와 해석을 같은 문맥에 표시한다.
 * assistant-ui GroupedParts는 일반 Tool만 하나의 ToolGroup으로 표현한다.
 */

import type { ChatModelRunResult, MessageStatus, ThreadMessageLike } from "@assistant-ui/react";
import type { ReadonlyJSONObject } from "assistant-stream/utils";

import type {
  ChatMessage,
  ChatMessageRunState,
  MessagePart,
  StatusStep,
  ObservedTiming,
} from "@/types/chat";
import { isStandaloneTool } from "./standalone-tools";
import { toolResultError } from "./tool-result";

export interface AgentMessageMetadata {
  /** Tool 호출과 별개로 Backend가 공개한 사용자용 업무 진행 단계. */
  statuses: StatusStep[];
  /** 현재 실행 Tool 직전에 공개된 안내 문구. */
  progressText?: string;
  observedTiming?: ObservedTiming;
  toolTimings?: Record<string, ObservedTiming>;
}

export function readAgentMetadata(
  custom: Record<string, unknown> | undefined,
): AgentMessageMetadata | undefined {
  if (!custom || !Array.isArray(custom.statuses)) return undefined;
  const progressText = typeof custom.progressText === "string"
    ? custom.progressText.trim()
    : "";
  return {
    statuses: custom.statuses as StatusStep[],
    observedTiming: custom.observedTiming as ObservedTiming | undefined,
    toolTimings: custom.toolTimings as Record<string, ObservedTiming> | undefined,
    ...(progressText ? { progressText } : {}),
  };
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
      part.kind === "tool" && !isStandaloneTool(part.toolName),
  );
  // 실행 과정 = 일반 Tool을 도착 순서대로 앞에 모은다(assistant-ui GroupedParts가 묶는다).
  const processParts = message.parts.filter(
    (part) => part.kind === "tool" && !isStandaloneTool(part.toolName),
  );
  const allStandaloneParts = message.parts.filter(
    (part): part is Extract<MessagePart, { kind: "tool" }> =>
      part.kind === "tool" && isStandaloneTool(part.toolName),
  );
  const standaloneParts = allStandaloneParts.filter((part, index) =>
    shouldShowStandalonePart(part, index, allStandaloneParts),
  );
  // 일반 Tool 사이의 준비 문구는 최종 답변에서 숨기되, 실행 중인 최신 Tool을
  // 설명하는 공개 문구는 progressText로 유지한다. 이미 제시한 표·차트가 있는
  // 문맥은 이후 추가 조회가 있어도 보존하고 마지막 구간은 답변으로 유지한다.
  const responseParts: MessagePart[] = [];
  let segment: MessagePart[] = [];
  let progressText: string | undefined;
  for (const part of message.parts) {
    if (part.kind === "tool" && !isStandaloneTool(part.toolName)) {
      if (segment.some((item) => item.kind === "tool")) {
        responseParts.push(...segment);
        progressText = undefined;
      } else {
        const candidate = segment
          .filter((item): item is Extract<MessagePart, { kind: "text" }> => item.kind === "text")
          .map((item) => item.text)
          .join("")
          .trim();
        // 새 Tool이 시작될 때 직전 공개 문구로 교체한다. 문구가 없으면 앞선
        // Tool의 안내를 계속 보여 주지 않는다.
        progressText = candidate || undefined;
      }
      segment = [];
    } else {
      segment.push(part);
    }
  }
  responseParts.push(...segment);
  const hasTrailingText = segment.some(
    (part) => part.kind === "text" && part.text.trim().length > 0,
  );
  const latestRegularTool = toolParts.at(-1);
  const visibleProgressText =
    message.runState.type === "running" &&
    latestRegularTool !== undefined &&
    latestRegularTool.result === undefined &&
    !hasTrailingText
      ? progressText
      : undefined;
  const visibleStandaloneIds = new Set(standaloneParts.map((part) => part.toolCallId));
  const contextualParts: MessagePart[] = [];
  for (const part of responseParts) {
    if (part.kind === "tool") {
      if (isStandaloneTool(part.toolName) && visibleStandaloneIds.has(part.toolCallId)) {
        contextualParts.push(part);
      }
      continue;
    }
    if (part.kind !== "text") continue;
    if (part.text.length > 0) contextualParts.push(part);
  }
  const visibleParts = [...processParts, ...contextualParts];
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
        ...(message.observedTiming ? { observedTiming: message.observedTiming } : {}),
        toolTimings: Object.fromEntries(message.parts.flatMap((part) =>
          part.kind === "tool" && part.observedTiming ? [[part.toolCallId, part.observedTiming]] : [],
        )),
        ...(visibleProgressText ? { progressText: visibleProgressText } : {}),
      },
    },
  };
}

/**
 * LocalRuntime `ChatModelAdapter`가 yield하는 assistant 스냅샷. `convertMessage`와 같은 변환을
 * 재사용하고, 분기 경로에서 Backend fork 지점을 찾을 수 있게 `turnId`를 metadata.custom에 싣는다.
 */
export function toRunResult(message: ChatMessage): ChatModelRunResult {
  const like = convertMessage(message);
  const content = typeof like.content === "string"
    ? [{ type: "text" as const, text: like.content }]
    : like.content;
  return {
    content: content as ChatModelRunResult["content"],
    status: like.status,
    metadata: {
      custom: {
        ...(like.metadata?.custom ?? {}),
        ...(message.turnId ? { turnId: message.turnId } : {}),
        ...(message.suggestions ? { suggestions: message.suggestions } : {}),
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
  // present_sql_preview는 args에 result_id가 없어 아래 공통 분기가 항상 그대로 보여준다.
  // present_chart·present_table·present_simulation은 result_id별로 dedup한다 — 한 턴에
  // 서로 다른 result_id로 여러 번 호출될 수 있으므로 Tool 이름만으로 묶지 않는다.
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
  return part.result !== undefined && toolResultError(part.result) === null;
}
