/** Copy/edit/reload composition from the official Thread element, plus the branch picker. */
import { ActionBarPrimitive, AuiIf, BranchPickerPrimitive, ErrorPrimitive, MessagePrimitive } from "@assistant-ui/react";
import { CheckIcon, ChevronLeftIcon, ChevronRightIcon, CopyIcon, PencilIcon, RefreshCwIcon } from "lucide-react";
import { ErrorState } from "./error-state";
import { ghostButton } from "./surfaces";
import { TooltipIconButton } from "./tooltip-icon-button";

/**
 * 편집·재생성은 이전 내용을 지우지 않고 분기로 남긴다. 대안이 둘 이상일 때만 표시한다.
 * 분기는 이번 브라우저 세션 동안만 유지된다.
 */
export function MessageBranchPicker({ user = false }: { user?: boolean }) {
  const noun = user ? "질문" : "답변";
  return (
    <BranchPickerPrimitive.Root hideWhenSingleBranch aria-label={`${noun} 버전 이동`} className="flex items-center gap-0.5 text-2xs tabular-nums text-ink-3">
      <BranchPickerPrimitive.Previous asChild>
        <TooltipIconButton tooltip={`이전 ${noun}`}><ChevronLeftIcon /></TooltipIconButton>
      </BranchPickerPrimitive.Previous>
      <span role="status" aria-live="polite">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <TooltipIconButton tooltip={`다음 ${noun}`}><ChevronRightIcon /></TooltipIconButton>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
}

export function MessageActions({ user = false }: { user?: boolean }) {
  return (
    <div className="flex items-center gap-1">
    <MessageBranchPicker user={user} />
    <ActionBarPrimitive.Root hideWhenRunning autohide="never" className="flex items-center gap-1">
      <ActionBarPrimitive.Copy asChild>
        <TooltipIconButton tooltip="복사">
          <AuiIf condition={(s) => s.message.isCopied}><CheckIcon /></AuiIf>
          <AuiIf condition={(s) => !s.message.isCopied}><CopyIcon /></AuiIf>
        </TooltipIconButton>
      </ActionBarPrimitive.Copy>
      {user ? (
        <ActionBarPrimitive.Edit asChild>
          <TooltipIconButton tooltip="편집"><PencilIcon /></TooltipIconButton>
        </ActionBarPrimitive.Edit>
      ) : (
        <ActionBarPrimitive.Reload asChild>
          <TooltipIconButton tooltip="재생성"><RefreshCwIcon /></TooltipIconButton>
        </ActionBarPrimitive.Reload>
      )}
      <AuiIf condition={(s) => s.message.isCopied}>
        <span role="status" className="text-2xs text-ink-3">복사됨</span>
      </AuiIf>
    </ActionBarPrimitive.Root>
    </div>
  );
}

export function MessageError() {
  return (
    <MessagePrimitive.Error>
      <ErrorState title="응답을 완료하지 못했습니다" detail={<ErrorPrimitive.Message />} action={
        <ActionBarPrimitive.Reload className={`${ghostButton} inline-flex items-center gap-1.5 px-2 py-1.5 text-2xs`}><RefreshCwIcon aria-hidden className="size-3.5" />이 질문 다시 실행</ActionBarPrimitive.Reload>
      } />
    </MessagePrimitive.Error>
  );
}
