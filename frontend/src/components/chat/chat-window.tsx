/**
 * 워크스페이스 셸 — 좌측 사이드바 / 중앙 대화 / 우측 인스펙터.
 * 대화 상태 · Streaming · AgentEvent 처리는 `useAgentChat` 훅이 담당한다
 * (hooks/use-agent-chat.ts). 이 컴포넌트는 레이아웃·패널 토글·세션 선택만
 * 다룬다. 상태관리는 React 기본(useState)만 사용한다.
 */

import { useCallback, useEffect, useState } from "react";
import { ChevronDownIcon } from "lucide-react";

import {
  AssistantRuntimeProvider,
  AuiIf,
  ThreadPrimitive,
} from "@assistant-ui/react";

import { SEED_CONVERSATION, SESSIONS } from "@/lib/dummy";
import { useAgentChat } from "@/hooks/use-agent-chat";
import { AppSidebar } from "./app-sidebar";
import { ContextInspector } from "./context-inspector";
import { ConnectionBanner } from "./connection-banner";
import { EmptyState } from "./empty-state";
import { MessageInput } from "./message-input";
import { AssistantMessage, UserEditComposer, UserMessage } from "./thread-messages";

const SEED_SESSION_ID = SESSIONS[0]?.id ?? null;

export function ChatWindow() {
  const {
    runtime,
    streaming,
    retryPrompt,
    handleRetry,
    resetConversation,
  } = useAgentChat(SEED_CONVERSATION);

  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    SEED_SESSION_ID,
  );
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);

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

  const handleNewChat = useCallback(() => {
    resetConversation([]);
    setActiveSessionId(null);
  }, [resetConversation]);

  const handleSelectSession = useCallback(
    (id: string) => {
      // 더미: 시드 세션만 대화를 갖는다. 나머지는 빈 대화로 연다.
      resetConversation(id === SEED_SESSION_ID ? SEED_CONVERSATION : []);
      setActiveSessionId(id);
    },
    [resetConversation],
  );

  const activeSession =
    SESSIONS.find((s) => s.id === activeSessionId) ?? null;

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
          {!inspectorOpen && (
            <IconButton
              label="인스펙터 펼치기"
              onClick={() => setInspectorOpen(true)}
            >
              <path d="M7.5 2.5 4 6l3.5 3.5" />
            </IconButton>
          )}
        </header>

        <ThreadPrimitive.Root className="relative flex min-h-0 flex-1 flex-col">
          <ThreadPrimitive.Viewport className="thin-scroll min-h-0 flex-1 overflow-y-auto px-4">
            <AuiIf condition={(s) => s.thread.isEmpty}>
              <EmptyState />
            </AuiIf>
            <AuiIf condition={(s) => !s.thread.isEmpty}>
              <div className="mx-auto flex max-w-reading flex-col gap-6 py-6">
                <ThreadPrimitive.Messages>
                  {({ message }) => {
                    if (message.composer.isEditing) return <UserEditComposer />;
                    if (message.role === "user") return <UserMessage />;
                    if (message.role === "assistant") return <AssistantMessage />;
                    return null;
                  }}
                </ThreadPrimitive.Messages>
              </div>
            </AuiIf>

            {retryPrompt && (
              <div className="mx-auto max-w-reading pb-4">
                <ConnectionBanner onRetry={handleRetry} retrying={streaming} />
              </div>
            )}
          </ThreadPrimitive.Viewport>

          <ThreadPrimitive.ScrollToBottom
            aria-label="맨 아래로 이동"
            className="absolute bottom-3 left-1/2 grid h-8 w-8 -translate-x-1/2 place-items-center rounded-full border border-line-strong bg-canvas text-ink-2 shadow-sm transition-opacity hover:bg-surface-2 disabled:pointer-events-none disabled:opacity-0"
          >
            <ChevronDownIcon className="size-4" />
          </ThreadPrimitive.ScrollToBottom>
        </ThreadPrimitive.Root>

        <div className="shrink-0">
          <MessageInput />
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
