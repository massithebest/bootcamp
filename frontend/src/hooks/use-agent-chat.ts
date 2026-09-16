/**
 * 대화 상태 · SSE Streaming · AgentEvent 처리 · assistant-ui 런타임 배선.
 *
 * `App` 루트에서 생성해 `chat-window.tsx`(3-pane 셸)에 전달한다 — 셸은 레이아웃/패널 토글/세션
 * 목록 표시만 맡고, 이 훅이 상태 소유권(React 기본 useState/useRef)과
 * assistant-ui 런타임 생성을 모두 갖는다. `useExternalStoreRuntime`을 쓰지만
 * 메시지 상태는 계속 우리가 소유한다 — assistant-ui는 상태/UI 플럼빙
 * 및 공통 Elements 계층을 담당한다.
 *
 * 편집/재생성(onEdit/onReload)은 백엔드 세션 포크가 필요해서
 * `turnId`(백엔드 `done` Event 의 `data.turn_id`)를 assistant 메시지에
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

import type { ChatMessage } from "@/types/chat";
import { createConversationId, sendChatMessage } from "@/lib/chat-api";
import { convertMessage } from "@/lib/chat-runtime";
import { applyAgentEvent, eventHasOutput, finishObservedTiming } from "@/lib/chat-state";

let idCounter = 0;
const nextId = (p: string) => `${p}-${Date.now()}-${(idCounter += 1)}`;

const emptyAssistant = (id: string, startedAt: number): ChatMessage => ({
  id,
  role: "assistant",
  content: "",
  parts: [],
  statuses: [],
  runState: { type: "running" },
  observedTiming: { startedAt },
});

const freshUser = (text: string): ChatMessage => ({
  id: nextId("user"),
  role: "user",
  content: text,
  parts: [],
  statuses: [],
  runState: { type: "complete" },
});

/** 재시도는 원래 사용자 메시지와 fork 지점을 그대로 재사용한다. */
interface RetryContext {
  text: string;
  prefixWithUser?: ChatMessage[];
  forkFromTurnId?: string;
  reuseUser?: boolean;
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
  const [retryContext, setRetryContext] = useState<RetryContext | null>(null);
  const conversationIdRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    conversationIdRef.current = createConversationId();
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const runRequest = useCallback(async (request: RetryContext) => {
    // React의 다음 render를 기다리지 않고 같은 tick의 중복 실행도 막는다.
    if (abortRef.current) return;
    const controller = new AbortController();
    abortRef.current = controller;
    const assistantId = nextId("assistant");
    const userMessage = freshUser(request.text);
    const startedAt = performance.now();
    setMessages((prev) => [
      ...(request.prefixWithUser ?? (request.reuseUser ? prev : [...prev, userMessage])),
      emptyAssistant(assistantId, startedAt),
    ]);
    setRetryContext(null);
    setStreaming(true);
    let hadOutput = false;
    const isCurrent = () => abortRef.current === controller && !controller.signal.aborted;

    try {
      const outcome = await sendChatMessage({
        message: request.text,
        conversationId: conversationIdRef.current || undefined,
        forkFromTurnId: request.forkFromTurnId,
        signal: controller.signal,
        onEvent: (event) => {
          if (!isCurrent()) return;
          hadOutput = eventHasOutput(event) || hadOutput;
          // updater는 StrictMode에서 재실행될 수 있으므로 ID는 밖에서 만든다.
          const partId = nextId("part");
          const observedAt = performance.now();
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? applyAgentEvent(m, event, partId, observedAt) : m,
            ),
          );
        },
      });
      if (!isCurrent()) return;
      if (outcome === "failed" && !hadOutput) {
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        setRetryContext({ ...request, reuseUser: true });
      }
    } finally {
      if (isCurrent()) {
        abortRef.current = null;
        setStreaming(false);
      }
    }
  }, []);

  const runTurn = useCallback(async (text: string) => {
    await runRequest({ text });
  }, [runRequest]);

  const runFromPrefix = useCallback(
    async (prefix: ChatMessage[], text: string, forkFromTurnId: string) => {
      await runRequest({
        text,
        prefixWithUser: [...prefix, freshUser(text)],
        forkFromTurnId,
      });
    },
    [runRequest],
  );

  const handleRetry = useCallback(() => {
    if (retryContext) void runRequest(retryContext);
  }, [retryContext, runRequest]);

  const handleStop = useCallback(() => {
    const observedAt = performance.now();
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setMessages((prev) =>
      prev.map((m) =>
        m.runState.type === "running"
          ? { ...m, runState: { type: "cancelled" }, observedTiming: finishObservedTiming(m.observedTiming, observedAt) }
          : m,
      ),
    );
  }, []);

  const resetConversation = useCallback((seed: ChatMessage[]) => {
    handleStop();
    setMessages(seed);
    setRetryContext(null);
    conversationIdRef.current = createConversationId();
  }, [handleStop]);

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

  /** 재생성 — 직전 사용자 입력과 이전 턴까지의 prefix로 다시 실행한다. */
  const handleReload = useCallback(
    async (parentId: string | null) => {
      if (!parentId) return;
      const idx = messages.findIndex((m) => m.id === parentId && m.role === "user");
      if (idx === -1) return;
      const replaced = messages.slice(idx + 1);
      if (replaced.some((m) => m.parts.length > 0) && !window.confirm(
        `이 답변과 이후 메시지 ${Math.max(0, replaced.length - 1)}개를 새 응답으로 교체합니다. 이전 내용은 복원할 수 없습니다. 다시 실행할까요?`,
      )) return;
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
    // 선형 대화만 지원한다. setMessages를 제공하면 assistant-ui가 branch/delete
    // capability를 활성화하므로, branch repository와 persistence를 함께 설계하기
    // 전에는 노출하지 않는다.
    onNew: handleNew,
    onCancel: handleCancel,
    onEdit: handleEdit,
    onReload: handleReload,
  });

  return {
    runtime,
    messages,
    streaming,
    retryPrompt: retryContext?.text ?? null,
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
