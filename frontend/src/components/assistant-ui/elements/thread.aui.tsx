/**
 * Adapted from https://r.assistant-ui.com/thread.json (2026-09-16).
 * Official Thread/ViewportFooter/composer/message composition, localized and
 * limited to the capabilities of the existing ExternalStoreRuntime.
 */
import { useEffect, useReducer, useRef, type ComponentProps, type ComponentType, type CSSProperties, type ReactNode } from "react";
import { AuiIf, ComposerPrimitive, MessagePartPrimitive, MessagePrimitive, ThreadPrimitive } from "@assistant-ui/react";
import { ArrowDownIcon, ArrowUpIcon, ChevronDownIcon, GaugeIcon, PlusIcon, SparklesIcon, SquareIcon } from "lucide-react";
import { MessageActions, MessageError } from "./message-actions.aui";
import { TooltipIconButton } from "./tooltip-icon-button";
import { EditMessage } from "./edit-message.aui";
import { MarkdownText } from "./markdown-text";

export interface ThreadComponents {
  Welcome?: ComponentType;
  Suggestions?: ComponentType;
  AssistantMessage?: ComponentType;
}

const EMPTY_COMPONENTS: ThreadComponents = {};

export function Thread({ components = EMPTY_COMPONENTS, notice, autoFocus = true, autoScroll = true }: {
  components?: ThreadComponents;
  notice?: ReactNode;
  autoFocus?: boolean;
  autoScroll?: boolean;
}) {
  const { Welcome = ThreadWelcome, Suggestions = ThreadSuggestions, AssistantMessage: Assistant = AssistantMessage } = components;
  return (
    <ThreadPrimitive.Root className="aui-root relative flex min-h-0 flex-1 flex-col bg-canvas" style={{ "--thread-max-width": "47.5rem" } as CSSProperties}>
      <ThreadPrimitive.Viewport
        data-slot="aui_thread-viewport"
        turnAnchor="bottom"
        autoScroll={autoScroll}
        className="thin-scroll relative flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden px-4"
      >
        <div className="mx-auto flex w-full max-w-[var(--thread-max-width)] flex-1 flex-col">
          <AuiIf condition={(s) => s.thread.isEmpty && !s.thread.isLoading}>
            <div className="my-auto flex w-full flex-col items-center gap-6 py-12">
              <Welcome />
              <Composer autoFocus={autoFocus} />
              <Suggestions />
            </div>
          </AuiIf>
          <AuiIf condition={(s) => s.thread.isLoading}>
            <p role="status" className="py-6 text-ui text-ink-3">대화를 불러오는 중…</p>
          </AuiIf>
          <div data-slot="aui_message-group" className="flex flex-col gap-6 py-6 empty:hidden">
            <ThreadPrimitive.Messages>
              {({ message }) => {
                if (message.composer.isEditing) return <EditComposer />;
                if (message.role === "user") return <UserMessage />;
                if (message.role === "assistant") return <Assistant />;
                return null;
              }}
            </ThreadPrimitive.Messages>
          </div>
          {notice && <div className="pb-4">{notice}</div>}
          <AuiIf condition={(s) => !s.thread.isEmpty}>
            <ThreadPrimitive.ViewportFooter className="sticky bottom-0 mt-auto flex flex-col gap-2 bg-canvas pb-5 pt-3">
              <ThreadPrimitive.ScrollToBottom asChild>
                <TooltipIconButton tooltip="맨 아래로 이동" className="absolute -top-9 left-1/2 -translate-x-1/2 border border-line-strong bg-canvas shadow-sm disabled:invisible">
                  <ArrowDownIcon />
                </TooltipIconButton>
              </ThreadPrimitive.ScrollToBottom>
              <p className="text-center text-2xs text-ink-3">결과의 근거와 데이터 범위를 함께 확인하세요.</p>
              <Composer autoFocus={autoFocus} />
            </ThreadPrimitive.ViewportFooter>
          </AuiIf>
        </div>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
}

function ThreadWelcome() {
  return <h2 className="text-center text-2xl font-semibold tracking-tight">무엇을 도와드릴까요?</h2>;
}

function ThreadSuggestions() {
  return null;
}

function Composer({ autoFocus }: { autoFocus: boolean }) {
  return (
    <ComposerPrimitive.Root className="aui-composer-root flex min-h-16 w-full flex-col gap-0 rounded-2xl border border-line-strong bg-canvas px-4 py-2 shadow-sm transition-[border-color,box-shadow] focus-within:border-accent focus-within:shadow-[0_0_0_1px_var(--accent-weak)]">
      <ComposerInput
        data-slot="aui_composer-input"
        rows={1}
        submitMode="enter"
        autoFocus={autoFocus}
        aria-label="메시지 입력"
        placeholder="생산계획 데이터에 대해 질문하세요. 예: 제품별 WIP를 보여줘"
        className="max-h-44 min-h-6 w-full resize-none bg-transparent text-ui text-ink outline-none placeholder:text-ink-3 focus-visible:outline-none disabled:opacity-60"
      />
      <div className="flex min-w-0 items-center justify-between gap-2">
        <div className="flex min-w-0 translate-y-1 items-center gap-1 text-2xs text-ink-2">
          <TooltipIconButton
            tooltip="첨부 기능 준비 중"
            disabled
            className="size-7 cursor-default rounded-full disabled:cursor-default disabled:opacity-100"
          >
            <PlusIcon />
          </TooltipIconButton>
          <button
            type="button"
            aria-disabled="true"
            tabIndex={-1}
            title="표시 모델: GLM-5.3-Flash · 모델 설정 조회·선택 기능은 준비 중입니다."
            aria-label="모델 GLM-5.3-Flash, 설정 기능 미연결"
            className="inline-flex h-7 min-w-0 cursor-default items-center gap-1 rounded-md px-1.5 text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <SparklesIcon className="size-3.5 shrink-0" aria-hidden />
            <span className="truncate">GLM-5.3-Flash</span>
            <ChevronDownIcon className="size-3 shrink-0 text-ink-3" aria-hidden />
          </button>
          <button
            type="button"
            aria-disabled="true"
            tabIndex={-1}
            title="표시 추론 강도: 중간 · 추론 강도 조절 기능은 준비 중입니다."
            aria-label="추론 강도 중간, 조절 기능 미연결"
            className="inline-flex h-7 cursor-default items-center gap-1 rounded-md px-1.5 text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <GaugeIcon className="size-3.5" aria-hidden />
            <span className="whitespace-nowrap">중간</span>
            <ChevronDownIcon className="size-3 text-ink-3" aria-hidden />
          </button>
        </div>
        <div className="flex shrink-0 items-center gap-2">
        <AuiIf condition={(s) => !s.thread.isRunning}>
          <ComposerPrimitive.Send asChild>
            <TooltipIconButton tooltip="전송" className="size-8 rounded-lg bg-accent text-accent-ink hover:bg-accent-hover hover:text-accent-ink disabled:bg-surface-2 disabled:text-ink-3"><ArrowUpIcon /></TooltipIconButton>
          </ComposerPrimitive.Send>
        </AuiIf>
        <AuiIf condition={(s) => s.thread.isRunning}>
          <ComposerPrimitive.Cancel asChild>
            <TooltipIconButton tooltip="중단" className="size-8 rounded-lg bg-ink text-canvas hover:bg-ink-2 hover:text-canvas"><SquareIcon className="fill-current" /></TooltipIconButton>
          </ComposerPrimitive.Cancel>
        </AuiIf>
        </div>
      </div>
    </ComposerPrimitive.Root>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root data-role="user" className="flex min-w-0 flex-col items-end gap-1">
      <h2 className="sr-only">사용자 질문</h2>
      <div className="max-w-[85%] whitespace-pre-wrap [overflow-wrap:anywhere] rounded border border-line-strong bg-surface px-3 py-2 text-ui">
        <MessagePrimitive.Parts>{({ part }) => part.type === "text" ? <MessagePartPrimitive.Text /> : null}</MessagePrimitive.Parts>
      </div>
      <MessageActions user />
    </MessagePrimitive.Root>
  );
}

function EditComposer() {
  return (
    <EditMessage>
      <ComposerInput aria-label="메시지 편집" autoFocus submitMode="enter" className="max-h-44 resize-none bg-transparent text-ui text-ink" />
    </EditMessage>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root data-role="assistant" className="flex min-w-0 flex-col gap-3">
      <MessagePrimitive.Parts>{({ part }) => part.type === "text" ? <MarkdownText /> : null}</MessagePrimitive.Parts>
      <MessageError />
      <MessageActions />
    </MessagePrimitive.Root>
  );
}

/** Autosize remeasures on render/window resize, but pane width also animates
 * after that event. Observe width only so the settled layout is remeasured
 * without taking ownership of the runtime's text, focus, or input handling. */
function ComposerInput(props: ComponentProps<typeof ComposerPrimitive.Input>) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [, remeasure] = useReducer((value: number) => value + 1, 0);
  useEffect(() => {
    const input = ref.current;
    if (!input) return;
    let previousWidth = input.clientWidth;
    const observer = new ResizeObserver(() => {
      if (input.clientWidth !== previousWidth) {
        previousWidth = input.clientWidth;
        remeasure();
      }
    });
    observer.observe(input);
    return () => observer.disconnect();
  }, []);
  return <ComposerPrimitive.Input {...props} ref={ref} />;
}
