/**
 * 좌측 사이드바 — 세션 목록.  시간 그룹핑 + 세션에서 쓰인 도구 흔적 표식.
 */

import type { Session, ToolTrace } from "@/types/workspace";
import { CURRENT_USER } from "@/lib/dummy";

const GROUP_LABEL: Record<Session["group"], string> = {
  today: "오늘",
  week: "지난 7일",
  earlier: "이전",
};

const GROUP_ORDER: Session["group"][] = ["today", "week", "earlier"];

const TRACE_GLYPH: Record<ToolTrace, string> = {
  query: "조",
  document: "문",
  simulation: "시",
};

function TraceMarks({ traces }: { traces: ToolTrace[] }) {
  return (
    <span className="flex shrink-0 gap-0.5">
      {(["query", "document", "simulation"] as ToolTrace[]).map((t) => {
        const on = traces.includes(t);
        return (
          <span
            key={t}
            title={
              t === "query"
                ? "생산 실적 조회"
                : t === "document"
                  ? "공정 문서 검색"
                  : "시뮬레이션 실행"
            }
            className={`grid h-3.5 w-3.5 place-items-center rounded-[3px] font-mono text-[0.5625rem] leading-none ${
              on
                ? t === "simulation"
                  ? "bg-accent-weak text-accent"
                  : "bg-surface-2 text-ink-2"
                : "text-line-strong"
            }`}
          >
            {on ? TRACE_GLYPH[t] : "·"}
          </span>
        );
      })}
    </span>
  );
}

export function AppSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onCollapse,
}: {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onCollapse: () => void;
}) {
  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center gap-2 border-b border-line px-3 py-3">
        <span className="grid h-5 w-5 place-items-center rounded-[4px] bg-accent text-[0.5625rem] font-bold tracking-tight text-accent-ink">
          FP
        </span>
        <span className="flex-1 text-ui font-semibold text-ink">
          P&amp;T FP agent
        </span>
        <button
          type="button"
          onClick={onCollapse}
          aria-label="사이드바 접기"
          className="rounded p-1 text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink"
        >
          <svg viewBox="0 0 12 12" width="13" height="13" aria-hidden>
            <path
              d="M7.5 2.5 4 6l3.5 3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      <div className="px-3 py-2">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full rounded border border-line-strong bg-canvas px-2.5 py-1.5 text-left text-ui font-medium text-ink transition-colors hover:border-accent hover:text-accent"
        >
          + 새 대화
        </button>
      </div>

      <nav className="thin-scroll flex-1 overflow-y-auto px-2 pb-3">
        {GROUP_ORDER.map((group) => {
          const items = sessions.filter((s) => s.group === group);
          if (items.length === 0) return null;
          return (
            <div key={group} className="mb-2">
              <p className="px-1.5 py-1 text-2xs font-medium text-ink-3">
                {GROUP_LABEL[group]}
              </p>
              <ul>
                {items.map((s) => {
                  const active = s.id === activeSessionId;
                  return (
                    <li key={s.id}>
                      <button
                        type="button"
                        onClick={() => onSelectSession(s.id)}
                        aria-current={active ? "true" : undefined}
                        className={`group flex w-full items-center gap-2 rounded px-1.5 py-1.5 text-left transition-colors ${
                          active
                            ? "border-l-2 border-accent bg-accent-weak"
                            : "border-l-2 border-transparent hover:bg-surface-2"
                        }`}
                      >
                        <span className="min-w-0 flex-1">
                          <span
                            className={`block truncate text-ui ${
                              active ? "font-medium text-ink" : "text-ink-2"
                            }`}
                          >
                            {s.title}
                          </span>
                          <span className="block text-2xs text-ink-3">
                            {s.lastActivity}
                          </span>
                        </span>
                        <TraceMarks traces={s.traces} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>

      <div className="border-t border-line px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-surface-2 text-2xs font-medium text-ink-2">
            {CURRENT_USER.name.slice(0, 1)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-ui text-ink">
              {CURRENT_USER.name}
            </span>
            <span className="block truncate text-2xs text-ink-3">
              {CURRENT_USER.team}
            </span>
          </span>
          <button
            type="button"
            className="rounded p-1 text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink"
            aria-label="설정"
          >
            <svg viewBox="0 0 14 14" width="14" height="14" aria-hidden>
              <circle
                cx="7"
                cy="7"
                r="2.2"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.3"
              />
              <path
                d="M7 1.4v1.6M7 11v1.6M12.6 7H11M3 7H1.4M10.9 3.1l-1.1 1.1M4.2 9.8l-1.1 1.1M10.9 10.9l-1.1-1.1M4.2 4.2 3.1 3.1"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
