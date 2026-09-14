/**
 * 대화 상태 · SSE Streaming · AgentEvent 처리 · assistant-ui 런타임 배선.
 *
 * `chat-window.tsx`(3-pane 셸)에서 분리했다 — 셸은 레이아웃/패널 토글/세션
 * 목록 표시만 맡고, 이 훅이 상태 소유권(React 기본 useState/useRef)과
 * assistant-ui 런타임 생성을 모두 갖는다. `useExternalStoreRuntime`을 쓰지만
 * 메시지 상태는 계속 우리가 소유한다 — assistant-ui는 상태/UI 플럼빙
 * 계층일 뿐이다.
 *
 * 편집/재생성(onEdit/onReload)은 백엔드 세션 포크가 필요해서(docs/decisions.md
 * Q5) `turnId`(백엔드 `done` Event 의 `data.turn_id`)를 assistant 메시지에
 * 실어두고, 그 직전 turnId 를 포크 지점으로 다시 보낸다. 더미 시드 대화처럼
 * turnId 가 없는 메시지를 편집/재생성하면 그 대화를 처음부터 새로 시작한다
 * (`fork_from_turn_id: ""`) — 애초에 백엔드에 보낸 적이 없어 포크할 지점이
 * 없기 때문이다.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  useExternalStoreRuntime,
  type AppendMessage,
  type AssistantRuntime,
} from "@assistant-ui/react";

import type {
  AgentEvent,
  ChatMessage,
  StatusStep,
  StepStatus,
  ToolResult,
} from "@/types/chat";
import { createConversationId, sendChatMessage } from "@/lib/chat-api";
import { convertMessage } from "@/lib/chat-runtime";

let idCounter = 0;
const nextId = (p: string) => `${p}-${Date.now()}-${(idCounter += 1)}`;

const emptyAssistant = (id: string): ChatMessage => ({
  id,
  role: "assistant",
  content: "",
  parts: [],
  statuses: [],
  streaming: true,
  error: null,
});

const freshUser = (text: string): ChatMessage => ({
  id: nextId("user"),
  role: "user",
  content: text,
  parts: [],
  statuses: [],
  streaming: false,
  error: null,
});

/** 실패 시 재시도에 필요한 만큼만 기억한다. 편집/재생성 실패 후 "다시 시도"가
 *  포크 지점을 잃지 않도록 — 평범한 턴 실패는 이 값이 없다(runTurn 참고). */
interface RetryContext {
  text: string;
  forkFromTurnId: string;
  prefix: ChatMessage[];
}

export interface UseAgentChatResult {
  runtime: AssistantRuntime;
  messages: ChatMessage[];
  streaming: boolean;
  retryPrompt: string | null;
  handleRetry: () => void;
  handleStop: () => void;
  /** 대화를 초기화한다 — 진행 중인 요청 중단, 메시지를 `seed`로 교체,
   *  새 conversation_id 발급. `handleNewChat`/`handleSelectSession`이 쓴다. */
  resetConversation: (seed: ChatMessage[]) => void;
}

export function useAgentChat(initialMessages: ChatMessage[]): UseAgentChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [streaming, setStreaming] = useState(false);
  const [retryPrompt, setRetryPrompt] = useState<string | null>(null);

  const conversationIdRef = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const turnHadOutputRef = useRef(false);
  const retryContextRef = useRef<RetryContext | null>(null);

  useEffect(() => {
    conversationIdRef.current = createConversationId();
    return () => abortRef.current?.abort();
  }, []);

  const updateAssistant = useCallback(
    (id: string, fn: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
    },
    [],
  );

  const applyEvent = useCallback(
    (assistantId: string, event: AgentEvent) => {
      switch (event.type) {
        case "text": {
          const delta = event.content ?? "";
          if (!delta) return;
          turnHadOutputRef.current = true;
          updateAssistant(assistantId, (m) => {
            const last = m.parts[m.parts.length - 1];
            // 마지막 조각이 텍스트면 이어붙이고, 아니면(도구 결과 뒤) 새 조각 시작.
            if (last && last.kind === "text") {
              const parts = m.parts.slice();
              parts[parts.length - 1] = { ...last, text: last.text + delta };
              return { ...m, parts };
            }
            return {
              ...m,
              parts: [...m.parts, { kind: "text", id: nextId("txt"), text: delta }],
            };
          });
          return;
        }
        case "status": {
          const step = readStatusStep(event);
          if (!step) return;
          turnHadOutputRef.current = true;
          updateAssistant(assistantId, (m) => ({
            ...m,
            statuses: upsertStatus(m.statuses, step),
          }));
          return;
        }
        case "tool_call": {
          const step = readStatusStep(event, "running");
          if (step) {
            turnHadOutputRef.current = true;
            updateAssistant(assistantId, (m) => ({
              ...m,
              statuses: upsertStatus(m.statuses, step),
            }));
          }
          return;
        }
        case "tool_result": {
          turnHadOutputRef.current = true;
          const result: ToolResult = {
            id: nextId("tool"),
            toolName: event.tool_name ?? "tool",
            data: event.data ?? null,
            content: event.content ?? null,
          };
          // `execute_sql` 의 purpose 는 결과에 실려 온다. 진행 표시의 해당 단계에 붙인다.
          const purpose = asString(result.data?.purpose);
          updateAssistant(assistantId, (m) => ({
            ...m,
            parts: [...m.parts, { kind: "tool", id: result.id, result }],
            statuses: purpose
              ? annotateStatus(m.statuses, result.toolName, purpose)
              : m.statuses,
          }));
          return;
        }
        case "error": {
          updateAssistant(assistantId, (m) => ({
            ...m,
            error:
              event.content ?? "요청을 처리하는 중 오류가 발생했습니다.",
          }));
          return;
        }
        case "done": {
          // turn_id 는 이 턴의 포크 지점 — 편집/재생성이 나중에 참조한다.
          const turnId = asString(event.data?.turn_id);
          updateAssistant(assistantId, (m) => ({
            ...m,
            streaming: false,
            turnId: turnId ?? m.turnId,
          }));
          return;
        }
      }
    },
    [updateAssistant],
  );

  /**
   * 스트리밍 실행 공통부. 호출 측이 `messages` 를 원하는 형태로 미리
   * 세팅해두고(새 user 메시지 + emptyAssistant 까지 포함) 호출한다.
   * 반환값이 `true` 면 무출력 실패 — 호출 측이 배너/재시도 컨텍스트를 정리한다.
   */
  const streamTurn = useCallback(
    async (
      assistantId: string,
      text: string,
      forkFromTurnId?: string,
    ): Promise<boolean> => {
      setStreaming(true);
      turnHadOutputRef.current = false;

      const controller = new AbortController();
      abortRef.current = controller;

      await sendChatMessage({
        message: text,
        conversationId: conversationIdRef.current || undefined,
        forkFromTurnId,
        signal: controller.signal,
        onEvent: (event) => applyEvent(assistantId, event),
      });

      updateAssistant(assistantId, (m) => ({ ...m, streaming: false }));
      setStreaming(false);
      abortRef.current = null;

      return !turnHadOutputRef.current && !controller.signal.aborted;
    },
    [applyEvent, updateAssistant],
  );

  const runTurn = useCallback(
    async (text: string, opts?: { retryOf?: string }) => {
      if (streaming) return;
      setRetryPrompt(null);
      retryContextRef.current = null;

      const assistantId = nextId("assistant");
      setMessages((prev) => {
        const base = opts?.retryOf
          ? prev.filter((m) => m.id !== opts.retryOf)
          : [...prev, freshUser(text)];
        return [...base, emptyAssistant(assistantId)];
      });

      const failed = await streamTurn(assistantId, text);

      // 출력이 하나도 없었으면 연결 실패로 간주하고 배너를 띄운다.
      if (failed) {
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        setRetryPrompt(text);
      }
    },
    [streaming, streamTurn],
  );

  /**
   * 편집/재생성 저수준 실행부. `prefix` 이후를 새 user 메시지 + 응답으로
   * 갈아 끼우고, `forkFromTurnId` 로 그 지점부터 백엔드 세션을 포크한다.
   */
  const runFromPrefix = useCallback(
    async (prefix: ChatMessage[], text: string, forkFromTurnId: string) => {
      if (streaming) return;
      setRetryPrompt(null);

      const assistantId = nextId("assistant");
      const userMessage = freshUser(text);
      setMessages([...prefix, userMessage, emptyAssistant(assistantId)]);

      const failed = await streamTurn(assistantId, text, forkFromTurnId);

      if (failed) {
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        setRetryPrompt(text);
        retryContextRef.current = { text, forkFromTurnId, prefix };
      } else {
        retryContextRef.current = null;
      }
    },
    [streaming, streamTurn],
  );

  const handleRetry = useCallback(() => {
    if (!retryPrompt) return;
    const ctx = retryContextRef.current;
    if (ctx) {
      runFromPrefix(ctx.prefix, ctx.text, ctx.forkFromTurnId);
    } else {
      runTurn(retryPrompt);
    }
  }, [retryPrompt, runTurn, runFromPrefix]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    );
  }, []);

  const resetConversation = useCallback(
    (seed: ChatMessage[]) => {
      handleStop();
      setMessages(seed);
      setRetryPrompt(null);
      retryContextRef.current = null;
      conversationIdRef.current = createConversationId();
    },
    [handleStop],
  );

  /* ---- assistant-ui 런타임 ---- */

  const handleNew = useCallback(
    async (message: AppendMessage) => {
      const text = appendMessageText(message);
      if (text) await runTurn(text);
    },
    [runTurn],
  );

  const handleCancel = useCallback(async () => {
    handleStop();
  }, [handleStop]);

  /** 재생성 — `parentId`(직전 user 메시지)는 그대로 재사용하고 응답만 새로 받는다. */
  const handleReload = useCallback(
    async (parentId: string | null) => {
      if (!parentId) return;
      const idx = messages.findIndex((m) => m.id === parentId && m.role === "user");
      if (idx === -1) return;
      const prefix = messages.slice(0, idx);
      await runFromPrefix(prefix, messages[idx].content, anchorTurnIdBefore(messages, idx));
    },
    [messages, runFromPrefix],
  );

  /** 편집 — `sourceId`(편집된 user 메시지)와 그 이후를 전부 새 턴으로 교체한다. */
  const handleEdit = useCallback(
    async (message: AppendMessage) => {
      const sourceId = message.sourceId;
      if (!sourceId) return;
      const idx = messages.findIndex((m) => m.id === sourceId);
      if (idx === -1) return;
      const text = appendMessageText(message);
      if (!text) return;
      const prefix = messages.slice(0, idx);
      await runFromPrefix(prefix, text, anchorTurnIdBefore(messages, idx));
    },
    [messages, runFromPrefix],
  );

  const runtime = useExternalStoreRuntime<ChatMessage>({
    messages,
    isRunning: streaming,
    convertMessage,
    setMessages: (next) => setMessages(next as ChatMessage[]),
    onNew: handleNew,
    onCancel: handleCancel,
    onEdit: handleEdit,
    onReload: handleReload,
  });

  return {
    runtime,
    messages,
    streaming,
    retryPrompt,
    handleRetry,
    handleStop,
    resetConversation,
  };
}

/**
 * `idx` 바로 앞 메시지(assistant)의 `turnId` — 편집/재생성의 포크 지점.
 * 그 assistant 메시지가 없거나 turnId 가 없으면(첫 턴이거나, 실제 백엔드
 * 턴을 거친 적 없는 더미 시드 메시지) 빈 문자열 — 대화를 처음부터 새로
 * 시작한다는 뜻이다(백엔드 `fork_from_turn_id: ""`, agent/agent.py 참고).
 */
function anchorTurnIdBefore(messages: ChatMessage[], idx: number): string {
  const prev = messages[idx - 1];
  return prev?.role === "assistant" && prev.turnId ? prev.turnId : "";
}

/** `AppendMessage` 의 content 에서 사용자 입력 텍스트만 꺼낸다. */
function appendMessageText(message: AppendMessage): string {
  return message.content
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join("")
    .trim();
}

/* ---- AgentEvent → StatusStep 파싱 (기존 로직 유지) ---- */

function readStatusStep(
  event: AgentEvent,
  defaultStatus: StepStatus = "running",
): StatusStep | null {
  const data = event.data ?? {};
  const step =
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
  return { step, label, status };
}

/** 이미 만들어진 진행 단계에 부가 설명을 붙인다. 해당 step 이 없으면 그대로 둔다. */
function annotateStatus(
  statuses: StatusStep[],
  step: string,
  detail: string,
): StatusStep[] {
  const idx = statuses.findIndex((s) => s.step === step);
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
