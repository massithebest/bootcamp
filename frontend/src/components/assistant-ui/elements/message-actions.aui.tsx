/** Copy/edit/reload composition from the official Thread element. */
import { ActionBarPrimitive, AuiIf, ErrorPrimitive, MessagePrimitive } from "@assistant-ui/react";
import { CheckIcon, CopyIcon, PencilIcon, RefreshCwIcon } from "lucide-react";
import { ErrorState } from "./error-state";
import { ghostButton } from "./surfaces";
import { TooltipIconButton } from "./tooltip-icon-button";

export function MessageActions({ user = false }: { user?: boolean }) {
  return (
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
