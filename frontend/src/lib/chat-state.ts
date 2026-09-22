/** 순수 AgentEvent 상태 전이. 상태·요청 수명주기의 소유자는 assistant-ui LocalRuntime과 lib/chat-model-adapter.ts다. */
import { parseSuggestions } from "./suggestions";
import type {
  AgentEvent, ChatMessage, StatusStep, StepStatus, ToolResult,
} from "@/types/chat";

export function applyAgentEvent(m: ChatMessage, event: AgentEvent, partId: string, observedAt?: number): ChatMessage {
  // A terminal event is final; error -> done may still supply the fork anchor.
  if ((m.runState.type === "complete" || m.runState.type === "cancelled") && event.type !== "done") return m;
  switch (event.type) {
    case "text": {
      const delta = event.content ?? "";
      if (!delta) return m;
      const last = m.parts.at(-1);
      if (last?.kind === "text") {
        return { ...m, parts: [...m.parts.slice(0, -1), { ...last, text: last.text + delta }] };
      }
      return {
        ...m,
        parts: [...m.parts, { kind: "text", id: partId, text: delta }],
      };
    }
    case "tool_call": {
      const toolName = event.tool_name ?? "tool";
      const toolCallId = event.tool_call_id ?? `${toolName}:${partId}`;
      const args = asRecord(event.data?.args);
      const step = readStatusStep({ ...event, tool_call_id: toolCallId });
      const toolPart: Extract<ChatMessage["parts"][number], { kind: "tool" }> = {
        kind: "tool",
        id: toolCallId,
        toolCallId,
        toolName,
        args,
        ...(observedAt !== undefined ? { observedTiming: { startedAt: observedAt } } : {}),
      };
      return {
        ...m,
        parts: upsertToolPart(m.parts, toolPart),
        statuses: step ? upsertStatus(m.statuses, step) : m.statuses,
      };
    }
    case "status": {
      const step = readStatusStep(event);
      return step ? { ...m, statuses: upsertStatus(m.statuses, step) } : m;
    }
    case "tool_result": {
      const toolName = event.tool_name ?? "tool";
      const pendingPart = [...m.parts].reverse().find(
        (part): part is Extract<ChatMessage["parts"][number], { kind: "tool" }> =>
          part.kind === "tool" && part.toolName === toolName && !part.result,
      );
      const toolCallId = event.tool_call_id ?? pendingPart?.toolCallId ?? partId;
      const result: ToolResult = {
        id: partId,
        toolCallId,
        toolName,
        data: event.data ?? null,
        content: event.content ?? null,
      };
      const purpose = asString(result.data?.purpose);
      const fallbackPart: Extract<ChatMessage["parts"][number], { kind: "tool" }> = {
        kind: "tool",
        id: toolCallId,
        toolCallId,
        toolName,
        args: null,
        result,
      };
      return {
        ...m,
        parts: updateToolResult(m.parts, fallbackPart, observedAt),
        statuses: purpose
          ? annotateStatus(m.statuses, toolCallId, toolName, purpose)
          : m.statuses,
      };
    }
    case "error":
      return {
        ...m,
        observedTiming: finishObservedTiming(m.observedTiming, observedAt),
        runState: {
          type: "error",
          message: event.content ?? "요청을 처리하는 중 오류가 발생했습니다.",
        },
      };
    case "done":
      return {
        ...m,
        observedTiming: finishObservedTiming(m.observedTiming, observedAt),
        runState: m.runState.type === "running" ? { type: "complete" } : m.runState,
        turnId: asString(event.data?.turn_id) ?? m.turnId,
        // 오류·취소 뒤의 done에는 후속질문을 붙이지 않는다.
        ...(m.runState.type === "running" ? { suggestions: parseSuggestions(event.data?.suggestions) } : {}),
      };
  }
}

export function finishObservedTiming(timing: ChatMessage["observedTiming"], now?: number) {
  if (!timing || timing.endedAt !== undefined || now === undefined) return timing;
  return { ...timing, endedAt: Math.max(timing.startedAt, now) };
}

export function eventHasOutput(event: AgentEvent): boolean {
  if (event.type === "text") return Boolean(event.content);
  if (event.type === "tool_result") return true;
  return (event.type === "status" || event.type === "tool_call") && readStatusStep(event) !== null;
}

function readStatusStep(
  event: AgentEvent,
  defaultStatus: StepStatus = "running",
): StatusStep | null {
  const data = event.data ?? {};
  const step =
    event.tool_call_id ??
    asString(data.step) ??
    asString(data.id) ??
    event.tool_name ??
    asString(data.name);

  if (!step) {
    if (event.type === "status" && event.content) {
      return {
        step: event.content,
        label: event.content,
        status: defaultStatus,
      };
    }
    return null;
  }

  const label =
    asString(data.label) ?? asString(data.title) ?? event.content ?? step;
  const status = normalizeStatus(asString(data.status)) ?? defaultStatus;
  const detail = asString(data.detail) ?? asString(data.purpose);
  const args = asRecord(data.args);
  return {
    step,
    label,
    status,
    ...(detail ? { detail } : {}),
    ...(event.tool_call_id ? { toolCallId: event.tool_call_id } : {}),
    ...(event.tool_name ? { toolName: event.tool_name } : {}),
    ...(args ? { args } : {}),
  };
}

/** 이미 만들어진 진행 단계에 부가 설명을 붙인다. 해당 step 이 없으면 그대로 둔다. */
function annotateStatus(
  statuses: StatusStep[],
  toolCallId: string,
  toolName: string,
  detail: string,
): StatusStep[] {
  let idx = statuses.findIndex((s) => s.step === toolCallId || s.toolCallId === toolCallId);
  if (idx === -1) idx = statuses.findLastIndex((s) => s.toolName === toolName || s.step === toolName);
  if (idx === -1) return statuses;
  const next = statuses.slice();
  next[idx] = { ...next[idx], detail };
  return next;
}

function upsertStatus(statuses: StatusStep[], incoming: StatusStep) {
  const idx = statuses.findIndex((s) => s.step === incoming.step);
  if (idx === -1) return [...statuses, incoming];
  const next = statuses.slice();
  next[idx] = { ...next[idx], ...incoming };
  return next;
}

function upsertToolPart(
  parts: ChatMessage["parts"],
  incoming: Extract<ChatMessage["parts"][number], { kind: "tool" }>,
): ChatMessage["parts"] {
  const idx = parts.findIndex(
    (part) => part.kind === "tool" && part.toolCallId === incoming.toolCallId,
  );
  if (idx === -1) return [...parts, incoming];
  const next = parts.slice();
  const current = next[idx];
  if (current.kind === "tool") next[idx] = { ...current, ...incoming, observedTiming: current.observedTiming ?? incoming.observedTiming };
  return next;
}

function updateToolResult(
  parts: ChatMessage["parts"],
  fallback: Extract<ChatMessage["parts"][number], { kind: "tool" }>,
  observedAt?: number,
): ChatMessage["parts"] {
  const idx = parts.findIndex(
    (part) => part.kind === "tool" && part.toolCallId === fallback.toolCallId,
  );
  if (idx === -1) return [...parts, fallback];
  const next = parts.slice();
  const current = next[idx];
  if (current.kind === "tool") next[idx] = {
    ...current,
    result: fallback.result,
    observedTiming: finishObservedTiming(current.observedTiming, observedAt),
  };
  return next;
}

function normalizeStatus(value: string | undefined): StepStatus | null {
  switch (value) {
    case "pending":
    case "running":
    case "completed":
    case "error":
      return value;
    case "done":
    case "complete":
      return "completed";
    case "start":
    case "in_progress":
      return "running";
    default:
      return null;
  }
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}
