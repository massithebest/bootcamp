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
import { KnowledgeManager, type KnowledgeManagerHandle } from "@/components/knowledge/knowledge-manager";
import { KnowledgeNavigation } from "@/components/knowledge/navigation";
import type { KnowledgeTarget } from "@/types/knowledge";
import type { Session } from "@/types/workspace";
import { EmptyState, ExampleSuggestions } from "./empty-state";
import { AssistantMessage } from "./thread-messages";

const SEED_SESSION_ID = SESSIONS[0]?.id ?? null;
const INSPECTOR_MIN_WIDTH = 16 * 16;
const INSPECTOR_MAX_WIDTH = 35 * 16;
const CHAT_MIN_WIDTH = 32.5 * 16;
const SIDEBAR_WIDTH = 15.5 * 16;
const INSPECTOR_RESIZE_STEP = 16;

const defaultInspectorWidth = (viewportWidth: number) => viewportWidth >= 1280 ? 23 * 16 : 20 * 16;
const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const THREAD_COMPONENTS = { Welcome: EmptyState, Suggestions: ExampleSuggestions, AssistantMessage };

export function ChatWindow({ chat }: { chat: UseAgentChatResult }) {
  const {
    runtime,
    streaming,
    retryPrompt,
    handleRetry,
    resetConversation,
  } = chat;

  const [view, setView] = useState<"chat" | "knowledge">("chat");
  const managerRef = useRef<KnowledgeManagerHandle>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef(0);
  const chatWidth = useRef<number>();
  const returnFocus = useRef<HTMLElement | null>(null);
  const managementTitle = useRef<HTMLHeadingElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const paneFocusFrame = useRef<number>();
  const go = useCallback((next: () => void) => {
    if (managerRef.current) managerRef.current.requestLeave(next); else next();
  }, []);
  const openKnowledge = useCallback((target?: KnowledgeTarget) => go(() => {
    if (view === "chat") {
      chatWidth.current = chatRef.current?.getBoundingClientRect().width;
      scrollRef.current = chatRef.current?.querySelector('[data-slot="aui_thread-viewport"]')?.scrollTop ?? 0;
      returnFocus.current = document.activeElement as HTMLElement;
    }
    managerRef.current?.open(target);
    setView("knowledge");
    requestAnimationFrame(() => managementTitle.current?.focus());
  }), [go, view]);
  const backToChat = useCallback(() => go(() => {
    setView("chat");
    requestAnimationFrame(() => {
      const viewport = chatRef.current?.querySelector('[data-slot="aui_thread-viewport"]');
      if (viewport) viewport.scrollTop = scrollRef.current;
      if (returnFocus.current?.isConnected) returnFocus.current.focus({ preventScroll: true });
    });
  }), [go]);

  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    SEED_SESSION_ID,
  );
  const [sessions, setSessions] = useState<Session[]>(SESSIONS);
  const localSessionSequence = useRef(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth);
  const [inspectorWidth, setInspectorWidth] = useState(() => defaultInspectorWidth(window.innerWidth));
  const [resizingInspector, setResizingInspector] = useState(false);
  const inspectorWidthCustomized = useRef(false);
  const inspectorResizeStart = useRef<{ pointerId: number; x: number; width: number } | null>(null);
  const paneReturnFocus = useRef<HTMLElement | null>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const inspectorRef = useRef<HTMLElement>(null);
  const sidebarOverlay = viewportWidth < 860;
  const inspectorOverlay = viewportWidth < 1180;
  const inspectorMinWidth = Math.min(INSPECTOR_MIN_WIDTH, Math.max(200, viewportWidth - 48));
  const inspectorMaxWidth = inspectorOverlay
    ? Math.max(inspectorMinWidth, Math.min(INSPECTOR_MAX_WIDTH, viewportWidth - 48))
    : Math.max(
      inspectorMinWidth,
      Math.min(INSPECTOR_MAX_WIDTH, viewportWidth - (sidebarOpen ? SIDEBAR_WIDTH : 0) - CHAT_MIN_WIDTH),
    );
  const renderedInspectorWidth = clamp(inspectorWidth, inspectorMinWidth, inspectorMaxWidth);
  const overlay = sidebarOpen && sidebarOverlay ? "sidebar" : view === "chat" && inspectorOpen && inspectorOverlay ? "inspector" : null;
  const closePane = useCallback((pane: "sidebar" | "inspector", restore = true) => {
    cancelAnimationFrame(paneFocusFrame.current ?? 0);
    if (pane === "sidebar") setSidebarOpen(false); else setInspectorOpen(false);
    if (restore) paneFocusFrame.current = requestAnimationFrame(() => {
      const target = paneReturnFocus.current;
      if (target?.isConnected) target.focus({ preventScroll: true });
      else (mainRef.current?.querySelector<HTMLElement>(`button[aria-label="${pane === "sidebar" ? "사이드바" : "인스펙터"} 펼치기"]`) ?? managementTitle.current)?.focus({ preventScroll: true });
    });
  }, []);
  const openPane = (pane: "sidebar" | "inspector", trigger: HTMLElement) => {
    cancelAnimationFrame(paneFocusFrame.current ?? 0);
    paneReturnFocus.current = trigger;
    if (pane === "sidebar") {
      setSidebarOpen(true);
      if (sidebarOverlay) setInspectorOpen(false);
    } else {
      setInspectorOpen(true);
      if (sidebarOverlay) setSidebarOpen(false);
    }
    paneFocusFrame.current = requestAnimationFrame(() => (pane === "sidebar" ? sidebarRef : inspectorRef).current?.querySelector<HTMLElement>("button:not(:disabled)")?.focus());
  };

  const resizeInspectorWithKeyboard = (event: React.KeyboardEvent<HTMLElement>) => {
    const multiplier = event.shiftKey ? 2 : 1;
    let nextWidth: number | undefined;
    if (event.key === "ArrowLeft") nextWidth = renderedInspectorWidth + INSPECTOR_RESIZE_STEP * multiplier;
    if (event.key === "ArrowRight") nextWidth = renderedInspectorWidth - INSPECTOR_RESIZE_STEP * multiplier;
    if (event.key === "Home") nextWidth = inspectorMinWidth;
    if (event.key === "End") nextWidth = inspectorMaxWidth;
    if (nextWidth === undefined) return;
    event.preventDefault();
    inspectorWidthCustomized.current = true;
    setInspectorWidth(clamp(nextWidth, inspectorMinWidth, inspectorMaxWidth));
  };
  const startInspectorResize = (event: React.PointerEvent<HTMLElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    inspectorResizeStart.current = { pointerId: event.pointerId, x: event.clientX, width: renderedInspectorWidth };
    setResizingInspector(true);
  };
  const moveInspectorResize = (event: React.PointerEvent<HTMLElement>) => {
    const start = inspectorResizeStart.current;
    if (!start || start.pointerId !== event.pointerId) return;
    inspectorWidthCustomized.current = true;
    setInspectorWidth(clamp(start.width + start.x - event.clientX, inspectorMinWidth, inspectorMaxWidth));
  };
  const finishInspectorResize = (event: React.PointerEvent<HTMLElement>) => {
    const start = inspectorResizeStart.current;
    if (!start || start.pointerId !== event.pointerId) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    inspectorResizeStart.current = null;
    setResizingInspector(false);
  };

  useEffect(() => {
    if (!resizingInspector) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  }, [resizingInspector]);
  useEffect(() => () => cancelAnimationFrame(paneFocusFrame.current ?? 0), []);
  const paneKeyDown = (event: React.KeyboardEvent<HTMLElement>, pane: "sidebar" | "inspector") => {
    if (overlay !== pane) return;
    if (event.key === "Escape") { event.preventDefault(); closePane(pane); }
    if (event.key === "Tab") {
      const element = event.currentTarget;
      // Non-modal panel: allow ordinary tab order, dismiss before outside focus is obscured.
      requestAnimationFrame(() => {
        if (!element.contains(document.activeElement)) closePane(pane, false);
      });
    }
  };

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
      setViewportWidth(width);
      if (!inspectorWidthCustomized.current) setInspectorWidth(defaultInspectorWidth(width));
      const prev = prevWidthRef.current;
      const crossedInspector = prev === null ? width < INSPECTOR_BREAKPOINT : prev >= INSPECTOR_BREAKPOINT && width < INSPECTOR_BREAKPOINT;
      const crossedSidebar = prev === null ? width < SIDEBAR_BREAKPOINT : prev >= SIDEBAR_BREAKPOINT && width < SIDEBAR_BREAKPOINT;
      if (crossedInspector) {
        if (inspectorRef.current?.contains(document.activeElement)) closePane("inspector");
        else setInspectorOpen(false);
      }
      if (crossedSidebar) {
        if (sidebarRef.current?.contains(document.activeElement)) closePane("sidebar");
        else setSidebarOpen(false);
      }
      prevWidthRef.current = width;
    };
    apply();
    window.addEventListener("resize", apply);
    return () => window.removeEventListener("resize", apply);
  }, [closePane]);

  const handleNewChat = useCallback(() => {
    setView("chat");
    const id = `local-current-${Date.now()}-${localSessionSequence.current++}`;
    runtime.thread.composer.setText("");
    resetConversation([]);
    setSessions((current) => [
      { id, title: "새 대화", lastActivity: "방금 전", group: "today", traces: [] },
      ...current.filter((session) => !session.id.startsWith("local-current-")),
    ]);
    setActiveSessionId(id);
  }, [resetConversation, runtime]);

  const handleSelectSession = useCallback(
    (id: string) => {
      setView("chat");
      // 더미: 시드 세션만 대화를 갖는다. 나머지는 빈 대화로 연다.
      runtime.thread.composer.setText("");
      resetConversation(id === SEED_SESSION_ID ? SEED_CONVERSATION : []);
      setSessions((current) => current.filter((session) => !session.id.startsWith("local-current-")));
      setActiveSessionId(id);
    },
    [resetConversation, runtime],
  );

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? null;

  return (
    <KnowledgeNavigation.Provider value={openKnowledge}><div className="relative grid h-screen w-full grid-cols-[auto_minmax(0,1fr)_auto] overflow-hidden bg-canvas text-ink">
      <a href="#workspace-main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:bg-canvas focus:p-2">작업 영역으로 이동</a>
      {overlay && <button type="button" tabIndex={-1} aria-label="열린 패널 닫기" className="absolute inset-0 z-20 bg-ink/10" onClick={() => closePane(overlay)} />}
      {/* 좌측 사이드바 */}
      <aside
        ref={sidebarRef}
        aria-label="대화 내비게이션"
        onKeyDown={event => paneKeyDown(event, "sidebar")}
        className={`${sidebarOverlay ? "absolute inset-y-0 left-0 z-30 bg-surface" : ""} h-full overflow-hidden border-r border-line transition-[width] duration-200 ease-panel ${
          sidebarOpen ? "w-[15.5rem]" : "w-0 border-r-0"
        }`}
      >
        <div className={`h-full w-[15.5rem] ${sidebarOpen ? "" : "invisible"}`}>
          <AppSidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={(id) => {
              if (id === activeSessionId) {
                if (view === "knowledge") backToChat();
              }
              else go(() => handleSelectSession(id));
            }}
            onNewChat={() => go(() => handleNewChat())}
            onOpenKnowledge={() => openKnowledge()}
            knowledgeActive={view === "knowledge"}
            onCollapse={() => closePane("sidebar")}
          />
        </div>
      </aside>

      {/* 중앙 대화 영역 */}
      <main ref={mainRef} id="workspace-main" tabIndex={-1} aria-label={view === "chat" ? "대화 작업 영역" : "지식 관리 작업 영역"} className="col-start-2 flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center gap-2 border-b border-line px-4">
          {!sidebarOpen && (
            <TooltipIconButton
              tooltip="사이드바 펼치기"
              onClick={event => openPane("sidebar", event.currentTarget)}
            >
              <PanelLeftOpenIcon />
            </TooltipIconButton>
          )}
          <div className="min-w-0 flex-1">
            <h1 ref={managementTitle} tabIndex={-1} className="truncate text-ui font-semibold text-ink outline-none">
              {view === "knowledge" ? "지식 관리" : activeSession ? activeSession.title : "새 대화"}
            </h1>
            <p className="text-2xs text-ink-2">
              {streaming
                ? "에이전트 실행 중…"
                : "생산계획 질의 · 시뮬레이션"}
            </p>
          </div>
          {view === "chat" && !inspectorOpen && (
            <TooltipIconButton
              tooltip="인스펙터 펼치기"
              onClick={event => openPane("inspector", event.currentTarget)}
            >
              <PanelRightOpenIcon />
            </TooltipIconButton>
          )}
        </header>

        <div className="relative flex min-h-0 flex-1 overflow-hidden">
          {/* Preserve measured viewport geometry: display:none resets bottom-follow intent. */}
          <div ref={chatRef} style={view === "knowledge" ? { position: "absolute", inset: "0 auto 0 0", width: chatWidth.current, visibility: "hidden", pointerEvents: "none" } : undefined} className="flex min-h-0 min-w-0 flex-1 flex-col" aria-hidden={view !== "chat"}>
            <Thread components={THREAD_COMPONENTS} autoScroll={view === "chat"} notice={retryPrompt ? <ConnectionBanner onRetry={handleRetry} retrying={streaming} /> : null} />
          </div>
          <div style={{ display: view === "knowledge" ? "flex" : "none" }} className="min-h-0 min-w-0 flex-1 flex-col" aria-hidden={view !== "knowledge"}>
            <KnowledgeManager ref={managerRef} />
          </div>
        </div>

      </main>

      {/* 우측 인스펙터 */}
      <aside
        ref={inspectorRef}
        aria-label="참고 정보 인스펙터"
        onKeyDown={event => paneKeyDown(event, "inspector")}
        style={{ width: view === "chat" && inspectorOpen ? renderedInspectorWidth : 0 }}
        className={`${inspectorOverlay ? "absolute inset-y-0 right-0 z-30 bg-surface" : "relative"} h-full overflow-hidden border-l border-line duration-200 ease-panel ${
          resizingInspector ? "transition-none" : "transition-[width]"
        } ${view === "chat" && inspectorOpen ? "" : "border-l-0"}`}
      >
        <div
          role="separator"
          aria-label="인스펙터 너비 조절"
          aria-orientation="vertical"
          aria-valuemin={Math.round(inspectorMinWidth)}
          aria-valuemax={Math.round(inspectorMaxWidth)}
          aria-valuenow={Math.round(renderedInspectorWidth)}
          aria-valuetext={`${Math.round(renderedInspectorWidth)}픽셀`}
          tabIndex={view === "chat" && inspectorOpen ? 0 : -1}
          title="드래그하거나 방향키로 인스펙터 너비 조절 · 더블클릭으로 기본 폭 복원"
          data-slot="inspector-resize-handle"
          onKeyDown={resizeInspectorWithKeyboard}
          onPointerDown={startInspectorResize}
          onPointerMove={moveInspectorResize}
          onPointerUp={finishInspectorResize}
          onPointerCancel={finishInspectorResize}
          onDoubleClick={() => {
            inspectorWidthCustomized.current = false;
            setInspectorWidth(clamp(defaultInspectorWidth(viewportWidth), inspectorMinWidth, inspectorMaxWidth));
          }}
          className={`group absolute inset-y-0 left-0 z-10 w-3 cursor-col-resize touch-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-[-2px] ${
            view === "chat" && inspectorOpen ? "" : "invisible"
          }`}
        >
          <span aria-hidden className="absolute left-1/2 top-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-line-strong transition-colors group-hover:bg-accent group-focus-visible:bg-accent" />
        </div>
        <div style={{ width: renderedInspectorWidth }} className={`h-full ${view === "chat" && inspectorOpen ? "" : "invisible"}`}>
          <ContextInspector onCollapse={() => closePane("inspector")} />
        </div>
      </aside>
    </div></KnowledgeNavigation.Provider>
  );
}
