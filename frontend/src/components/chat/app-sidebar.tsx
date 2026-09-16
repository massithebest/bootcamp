/** Base assistant-ui sidebar composition with a controlled, nonpersistent ThreadList. */
import { PanelLeftCloseIcon, PlusIcon, SettingsIcon } from "lucide-react";
import type { Session } from "@/types/workspace";
import { CURRENT_USER } from "@/lib/dummy";
import { ThreadList } from "@/components/assistant-ui/elements/thread-list";
import { TooltipIconButton } from "@/components/assistant-ui/elements/tooltip-icon-button";

const GROUP_LABEL = { today: "오늘", week: "지난 7일", earlier: "이전" };
const GROUP_ORDER: Session["group"][] = ["today", "week", "earlier"];

export function AppSidebar({ sessions, activeSessionId, onSelectSession, onNewChat, onCollapse }: {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onCollapse: () => void;
}) {
  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex h-16 shrink-0 items-center gap-2 border-b border-line px-3">
        <span className="grid size-6 place-items-center rounded bg-accent text-2xs font-semibold text-accent-ink">FP</span>
        <span className="flex-1 text-ui font-semibold">P&amp;T FP agent</span>
        <TooltipIconButton tooltip="사이드바 접기" onClick={onCollapse}><PanelLeftCloseIcon /></TooltipIconButton>
      </div>
      <div className="px-3 py-3">
        <button type="button" onClick={onNewChat} className="flex w-full items-center gap-2 rounded border border-line-strong bg-canvas px-3 py-2 text-ui text-ink hover:border-accent hover:text-accent">
          <PlusIcon className="size-3.5" /> 새 대화
        </button>
      </div>
      <p className="px-3 text-2xs text-ink-3">예시 세션 · 현재 대화만 유지됩니다</p>
      <nav aria-label="대화 목록" className="thin-scroll min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {GROUP_ORDER.map((group) => {
          const items = sessions.filter((s) => s.group === group);
          return items.length ? <ThreadList key={group} label={GROUP_LABEL[group]}
            threads={items.map((s) => ({ id: s.id, title: s.title, time: s.lastActivity }))}
            activeIndex={items.findIndex((s) => s.id === activeSessionId)}
            onActiveIndexChange={(index) => onSelectSession(items[index].id)} /> : null;
        })}
      </nav>
      <div className="flex items-center gap-2 border-t border-line px-3 py-3">
        <span className="grid size-7 shrink-0 place-items-center rounded bg-surface-2 text-2xs text-ink-2">{CURRENT_USER.name.slice(0, 1)}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-ui">{CURRENT_USER.name}</span>
          <span className="block truncate text-2xs text-ink-3">{CURRENT_USER.team} · 예시 사용자</span>
        </span>
        <TooltipIconButton tooltip="설정 (준비 중)" disabled title="설정 화면은 아직 연결되지 않았습니다"><SettingsIcon /></TooltipIconButton>
      </div>
    </div>
  );
}
