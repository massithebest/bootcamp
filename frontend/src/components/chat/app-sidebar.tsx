/** assistant-ui ThreadList primitives로 구성한 사이드바. 대화 목록은 이번 브라우저 세션 동안만 유지된다. */
import {
  ThreadListItemPrimitive,
  ThreadListPrimitive,
  useAuiState,
} from "@assistant-ui/react";
import {
  BookOpenIcon,
  MessageSquareIcon,
  PanelLeftCloseIcon,
  SettingsIcon,
  SquarePenIcon,
} from "lucide-react";
import { CURRENT_USER } from "@/lib/dummy";
import { cn } from "@/lib/utils";
import { TooltipIconButton } from "@/components/assistant-ui/elements/tooltip-icon-button";

const itemClass = "flex min-h-9 w-full items-center gap-2.5 rounded px-2.5 py-2 text-left text-ui transition-colors";

export function AppSidebar({ onSelectSession, onNewChat, onCollapse, onOpenKnowledge, knowledgeActive }: {
  onSelectSession: (id: string, active: boolean) => void;
  onNewChat: () => void;
  onCollapse: () => void;
  onOpenKnowledge: () => void;
  knowledgeActive: boolean;
}) {
  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex h-14 shrink-0 items-center gap-2 px-3">
        <span className="grid size-6 place-items-center rounded bg-accent text-2xs font-semibold text-accent-ink">FP</span>
        <span className="flex-1 text-ui font-semibold">P&amp;T FP agent</span>
        <TooltipIconButton tooltip="사이드바 접기" onClick={onCollapse}><PanelLeftCloseIcon /></TooltipIconButton>
      </div>
      <nav aria-label="주요 메뉴" className="shrink-0 space-y-0.5 px-2 pb-3">
        <button type="button" onClick={onNewChat} className={`${itemClass} text-ink hover:bg-surface-2`}>
          <SquarePenIcon className="size-4 shrink-0" aria-hidden />
          새 채팅
        </button>
        <button type="button" aria-current={knowledgeActive ? "page" : undefined} onClick={onOpenKnowledge} className={`${itemClass} ${knowledgeActive ? "bg-surface-2 font-semibold text-ink" : "text-ink-2 hover:bg-surface-2"}`}>
          <BookOpenIcon className="size-4 shrink-0" aria-hidden />
          지식 관리
        </button>
      </nav>
      <div className="flex min-h-0 flex-1 flex-col border-t border-line pt-2">
        <p className="px-4 py-1.5 text-2xs text-ink-3">최근 대화</p>
        <p className="px-4 pb-1 text-2xs text-ink-3">현재 브라우저 세션 동안만 유지됩니다</p>
        <nav aria-label="최근 대화" className="thin-scroll min-h-0 flex-1 overflow-y-auto px-2 pb-3">
          <ThreadListPrimitive.Root className="flex w-full flex-col gap-0.5">
            <PendingSession onSelectSession={onSelectSession} />
            <ThreadListPrimitive.Items>
              {() => <SessionItem onSelectSession={onSelectSession} />}
            </ThreadListPrimitive.Items>
          </ThreadListPrimitive.Root>
        </nav>
      </div>
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

function SessionItem({ onSelectSession }: { onSelectSession: (id: string, active: boolean) => void }) {
  const id = useAuiState((s) => s.threadListItem.id);
  const isMain = useAuiState((s) => s.threads.mainThreadId === s.threadListItem.id);
  const running = useAuiState((s) => s.threadListItem.isRunning);
  // 지식 관리를 열어 둔 동안에도 현재 대화 항목을 표시해 복귀 대상을 알린다.
  const current = isMain;
  return (
    <ThreadListItemPrimitive.Root>
      <ThreadListItemPrimitive.Trigger
        aria-current={current ? "true" : undefined}
        onClick={(event) => {
          // 지식 관리 화면의 미저장 변경 보호와 화면 복귀를 셸이 결정한다.
          event.preventDefault();
          onSelectSession(id, isMain);
        }}
        className={cn(
          "flex w-full items-start gap-2 rounded px-2 py-2 text-left transition-colors",
          current ? "bg-accent-weak text-ink" : "text-ink-2 hover:bg-surface-2",
        )}
      >
        <MessageSquareIcon className="mt-1 size-3.5 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-ui">
            <ThreadListItemPrimitive.Title fallback="새 대화" />
          </span>
          {running && <span className="block text-2xs text-ink-3">응답 중…</span>}
        </span>
      </ThreadListItemPrimitive.Trigger>
    </ThreadListItemPrimitive.Root>
  );
}

/** 아직 첫 질문을 보내지 않은 현재 새 대화. 목록 밖에 있어도 현재 위치와 복귀 대상을 보여 준다. */
function PendingSession({ onSelectSession }: { onSelectSession: (id: string, active: boolean) => void }) {
  const id = useAuiState((s) => (s.threads.newThreadId != null && s.threads.mainThreadId === s.threads.newThreadId ? s.threads.newThreadId : null));
  if (!id) return null;
  const current = true;
  return (
    <button
      type="button"
      aria-current={current ? "true" : undefined}
      onClick={() => onSelectSession(id, true)}
      className={cn(
        "flex w-full items-start gap-2 rounded px-2 py-2 text-left transition-colors",
        current ? "bg-accent-weak text-ink" : "text-ink-2 hover:bg-surface-2",
      )}
    >
      <MessageSquareIcon className="mt-1 size-3.5 shrink-0" aria-hidden />
      <span className="block min-w-0 flex-1 truncate text-ui">새 대화</span>
    </button>
  );
}
