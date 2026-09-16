/**
 * 워크스페이스 셸 — 좌측 사이드바 / 중앙 대화 / 우측 인스펙터.
 * 대화 상태 · Streaming · AgentEvent 처리는 `useAgentChat` 훅이 담당한다
 * (hooks/use-agent-chat.ts). 이 컴포넌트는 레이아웃·패널 토글·세션 선택만
 * 다룬다. 상태관리는 React 기본(useState)만 사용한다.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { PanelLeftOpenIcon, PanelRightOpenIcon } from "lucide-react";

import { Thread } from "@/components/assistant-ui/elements/thread.aui";
import { TooltipIconButton } from "@/components/assistant-ui/elements/tooltip-icon-button";
import { SEED_CONVERSATION, SESSIONS } from "@/lib/dummy";
import type { UseAgentChatResult } from "@/hooks/use-agent-chat";
import { AppSidebar } from "./app-sidebar";
import { ContextInspector } from "./context-inspector";
import { ConnectionBanner } from "./connection-banner";
import { EmptyState, ExampleSuggestions } from "./empty-state";
import { AssistantMessage } from "./thread-messages";

const SEED_SESSION_ID = SESSIONS[0]?.id ?? null;

const THREAD_COMPONENTS = { Welcome: EmptyState, Suggestions: ExampleSuggestions, AssistantMessage };

export function ChatWindow({ chat }: { chat: UseAgentChatResult }) {
  const {
    runtime,
    streaming,
    retryPrompt,
    handleRetry,
    resetConversation,
  } = chat;

  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    SEED_SESSION_ID,
  );
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  // 좁은 화면에서 패널을 자동으로 접는다 (자동으로 펼치지는 않는다).
  // 임계값을 "아래로 통과하는 순간"에만 접는다 — 이미 임계값 아래인 채로
  // 사용자가 직접 펼친 패널은, 그 폭에서 resize 이벤트가 더 발생해도
  // (창을 드래그하는 동안 수십 번 발생) 다시 강제로 닫지 않는다.
  const prevWidthRef = useRef<number | null>(null);
  useEffect(() => {
    const INSPECTOR_BREAKPOINT = 1180;
    const SIDEBAR_BREAKPOINT = 860;
    const apply = () => {
      const width = window.innerWidth;
      const prev = prevWidthRef.current;
      const crossedInspector = prev === null ? width < INSPECTOR_BREAKPOINT : prev >= INSPECTOR_BREAKPOINT && width < INSPECTOR_BREAKPOINT;
      const crossedSidebar = prev === null ? width < SIDEBAR_BREAKPOINT : prev >= SIDEBAR_BREAKPOINT && width < SIDEBAR_BREAKPOINT;
      if (crossedInspector) setInspectorOpen(false);
      if (crossedSidebar) setSidebarOpen(false);
      prevWidthRef.current = width;
    };
    apply();
    window.addEventListener("resize", apply);
    return () => window.removeEventListener("resize", apply);
  }, []);

  const handleNewChat = useCallback(() => {
    runtime.thread.composer.setText("");
    resetConversation([]);
    setActiveSessionId(null);
  }, [resetConversation, runtime]);

  const handleSelectSession = useCallback(
    (id: string) => {
      // 더미: 시드 세션만 대화를 갖는다. 나머지는 빈 대화로 연다.
      runtime.thread.composer.setText("");
      resetConversation(id === SEED_SESSION_ID ? SEED_CONVERSATION : []);
      setActiveSessionId(id);
    },
    [resetConversation, runtime],
  );

  const activeSession =
    SESSIONS.find((s) => s.id === activeSessionId) ?? null;

  return (
    <div className="grid h-screen w-full grid-cols-[auto_1fr_auto] overflow-hidden bg-canvas text-ink">
      {/* 좌측 사이드바 */}
      <aside
        className={`h-full overflow-hidden border-r border-line transition-[width] duration-200 ease-panel ${
          sidebarOpen ? "w-[15.5rem]" : "w-0 border-r-0"
        }`}
      >
        <div className={`h-full w-[15.5rem] ${sidebarOpen ? "" : "invisible"}`}>
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
      <header className="flex h-16 shrink-0 items-center gap-2 border-b border-line px-4">
          {!sidebarOpen && (
            <TooltipIconButton
              tooltip="사이드바 펼치기"
              onClick={() => setSidebarOpen(true)}
            >
              <PanelLeftOpenIcon />
            </TooltipIconButton>
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
            <TooltipIconButton
              tooltip="인스펙터 펼치기"
              onClick={() => setInspectorOpen(true)}
            >
              <PanelRightOpenIcon />
            </TooltipIconButton>
          )}
        </header>

        <Thread components={THREAD_COMPONENTS} notice={retryPrompt ? <ConnectionBanner onRetry={handleRetry} retrying={streaming} /> : null} />

      </section>

      {/* 우측 인스펙터 */}
      <aside
        className={`h-full overflow-hidden border-l border-line transition-[width] duration-200 ease-panel ${
          inspectorOpen ? "w-80" : "w-0 border-l-0"
        }`}
      >
        <div className={`h-full w-80 ${inspectorOpen ? "" : "invisible"}`}>
          <ContextInspector onCollapse={() => setInspectorOpen(false)} />
        </div>
      </aside>
    </div>
  );
}
