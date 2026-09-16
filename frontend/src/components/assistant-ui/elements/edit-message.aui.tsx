/** Runtime composition from assistant-ui elements/edit-message, with its discard warning. */
import type { ReactNode } from "react";
import { ComposerPrimitive, useAuiState } from "@assistant-ui/react";
import { AlertTriangleIcon } from "lucide-react";

export function EditMessage({ children }: { children: ReactNode }) {
  const discardedReplies = useAuiState((s) => s.thread.messages.slice(s.message.index + 1).filter((m) => m.role === "assistant").length);
  return (
    <ComposerPrimitive.Root data-slot="edit-message" className="ml-auto flex w-full max-w-[85%] flex-col gap-3 rounded border border-accent bg-surface p-3">
      {children}
      {discardedReplies > 0 && (
        <p role="note" className="flex items-start gap-2 text-2xs text-warn-ink">
          <AlertTriangleIcon aria-hidden className="size-3.5 shrink-0" />
          <span>다시 실행하면 이후 대화(답변 {discardedReplies}개)가 교체됩니다. 기존 대화로 되돌릴 수 없습니다.</span>
        </p>
      )}
      <div className="flex justify-end gap-2">
        <ComposerPrimitive.Cancel className="rounded px-2 py-1 text-2xs text-ink-2 hover:bg-surface-2">취소</ComposerPrimitive.Cancel>
        <ComposerPrimitive.Send className="rounded bg-accent px-2 py-1 text-2xs text-accent-ink disabled:opacity-40">저장하고 다시 실행</ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  );
}
