/**
 * 워크스페이스 셸 — 좌측 사이드바 / 중앙 대화 / 우측 인스펙터.
 * 대화 상태 · Streaming · AgentEvent 처리는 이 컴포넌트가 담당한다.
 * 상태관리는 React 기본(useState/useRef)만 사용한다.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  useExternalStoreRuntime,
  type AppendMessage,
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
import { SEED_CONVERSATION, SESSIONS } from "@/lib/dummy";
import { AppSidebar } from "./app-sidebar";
import { ContextInspector } from "./context-inspector";
import { ConnectionBanner } from "./connection-banner";
import { EmptyState } from "./empty-state";
import { MessageInput } from "./message-input";
import { AssistantMessage, UserMessage } from "./thread-messages";

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

const SEED_SESSION_ID = SESSIONS[0]?.id ?? null;

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>(SEED_CONVERSATION);
  const [streaming, setStreaming] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    SEED_SESSION_ID,
  );
  const [retryPrompt, setRetryPrompt] = useState<string | null>(null);

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  const conversationIdRef = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const turnHadOutputRef = useRef(false);

  useEffect(() => {
    conversationIdRef.current = createConversationId();
    return () => abortRef.current?.abort();
  }, []);

  // 좁은 화면에서 패널을 자동으로 접는다 (자동으로 펼치지는 않는다).
  useEffect(() => {
    const apply = () => {
      if (window.innerWidth < 1180) setInspectorOpen(false);
      if (window.innerWidth < 860) setSidebarOpen(false);
    };
    apply();
    window.addEventListener("resize", apply);
    return () => window.removeEventListener("resize", apply);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

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
          updateAssistant(assistantId, (m) => ({ ...m, streaming: false }));
          return;
        }
      }
    },
    [updateAssistant],
  );

  const runTurn = useCallback(
    async (text: string, opts?: { retryOf?: string }) => {
      if (streaming) return;
      setRetryPrompt(null);

      const assistantId = nextId("assistant");
      setMessages((prev) => {
        const base = opts?.retryOf
          ? prev.filter((m) => m.id !== opts.retryOf)
          : [
              ...prev,
              {
                id: nextId("user"),
                role: "user" as const,
                content: text,
                parts: [],
                statuses: [],
                streaming: false,
                error: null,
              },
            ];
        return [...base, emptyAssistant(assistantId)];
      });
      setStreaming(true);
      turnHadOutputRef.current = false;

      const controller = new AbortController();
      abortRef.current = controller;

      await sendChatMessage({
        message: text,
        conversationId: conversationIdRef.current || undefined,
        signal: controller.signal,
        onEvent: (event) => applyEvent(assistantId, event),
      });

      updateAssistant(assistantId, (m) => ({ ...m, streaming: false }));
      setStreaming(false);
      abortRef.current = null;

      // 출력이 하나도 없었으면 연결 실패로 간주하고 배너를 띄운다.
      if (!turnHadOutputRef.current && !controller.signal.aborted) {
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
        setRetryPrompt(text);
      }
    },
    [streaming, applyEvent, updateAssistant],
  );

  const handleSend = useCallback((text: string) => runTurn(text), [runTurn]);

  const handleRetry = useCallback(() => {
    if (retryPrompt) runTurn(retryPrompt);
  }, [retryPrompt, runTurn]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    );
  }, []);

  const handleNewChat = useCallback(() => {
    handleStop();
    setMessages([]);
    setRetryPrompt(null);
    setActiveSessionId(null);
    conversationIdRef.current = createConversationId();
  }, [handleStop]);

  const handleSelectSession = useCallback(
    (id: string) => {
      handleStop();
      setActiveSessionId(id);
      setRetryPrompt(null);
      // 더미: 시드 세션만 대화를 갖는다. 나머지는 빈 대화로 연다.
      setMessages(id === SEED_SESSION_ID ? SEED_CONVERSATION : []);
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

  const runtime = useExternalStoreRuntime<ChatMessage>({
    messages,
    isRunning: streaming,
    convertMessage,
    setMessages: (next) => setMessages(next as ChatMessage[]),
    onNew: handleNew,
    onCancel: handleCancel,
  });

  const activeSession =
    SESSIONS.find((s) => s.id === activeSessionId) ?? null;
  const isEmpty = messages.length === 0;

  return (
    <AssistantRuntimeProvider runtime={runtime}>
    <div className="grid h-screen w-full grid-cols-[auto_1fr_auto] overflow-hidden bg-canvas text-ink">
      {/* 좌측 사이드바 */}
      <aside
        className={`h-full overflow-hidden border-r border-line transition-[width] duration-200 ease-panel ${
          sidebarOpen ? "w-[15.5rem]" : "w-0 border-r-0"
        }`}
      >
        <div className="h-full w-[15.5rem]">
          <AppSidebar
            sessions={SESSIONS}
            activeSessionId={activeSessionId}
            onSelectSession={handleSelectSession}
            onNewChat={handleNewChat}
            onCollapse={() => setSidebarOpen(false)}
          />
        </div>
      </aside>

      {/* 중앙 대화 영역 */}
      <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
        <header className="flex shrink-0 items-center gap-2 border-b border-line px-4 py-2.5">
          {!sidebarOpen && (
            <IconButton
              label="사이드바 펼치기"
              onClick={() => setSidebarOpen(true)}
            >
              <path d="M4.5 2.5 8 6l-3.5 3.5" />
            </IconButton>
          )}
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-ui font-semibold text-ink">
              {activeSession ? activeSession.title : "새 대화"}
            </h1>
            <p className="text-2xs text-ink-3">
              {streaming
                ? "에이전트 실행 중…"
                : "생산계획 질의 · 시뮬레이션"}
            </p>
          </div>
          {streaming && (
            <button
              type="button"
              onClick={handleStop}
              className="rounded border border-line-strong px-2 py-1 text-2xs text-ink-2 transition-colors hover:bg-surface-2"
            >
              중단
            </button>
          )}
          {!inspectorOpen && (
            <IconButton
              label="인스펙터 펼치기"
              onClick={() => setInspectorOpen(true)}
            >
              <path d="M7.5 2.5 4 6l3.5 3.5" />
            </IconButton>
          )}
        </header>

        <ThreadPrimitive.Root className="flex min-h-0 flex-1 flex-col">
          <ThreadPrimitive.Viewport className="thin-scroll min-h-0 flex-1 overflow-y-auto px-4">
            {isEmpty ? (
              <EmptyState onPick={handleSend} />
            ) : (
              <div className="mx-auto flex max-w-reading flex-col gap-6 py-6">
                <ThreadPrimitive.Messages
                  components={{ UserMessage, AssistantMessage }}
                />
              </div>
            )}

            {retryPrompt && (
              <div className="mx-auto max-w-reading pb-4">
                <ConnectionBanner onRetry={handleRetry} retrying={streaming} />
              </div>
            )}
          </ThreadPrimitive.Viewport>
        </ThreadPrimitive.Root>

        <div className="shrink-0">
          <MessageInput disabled={streaming} onSend={handleSend} />
        </div>
      </section>

      {/* 우측 인스펙터 */}
      <aside
        className={`h-full overflow-hidden border-l border-line transition-[width] duration-200 ease-panel ${
          inspectorOpen ? "w-80" : "w-0 border-l-0"
        }`}
      >
        <div className="h-full w-80">
          <ContextInspector onCollapse={() => setInspectorOpen(false)} />
        </div>
      </aside>
    </div>
    </AssistantRuntimeProvider>
  );
}

/** `AppendMessage` 의 content 에서 사용자 입력 텍스트만 꺼낸다. */
function appendMessageText(message: AppendMessage): string {
  return message.content
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join("")
    .trim();
}

function IconButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="rounded p-1 text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink"
    >
      <svg viewBox="0 0 12 12" width="13" height="13" aria-hidden>
        <g
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {children}
        </g>
      </svg>
    </button>
  );
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
