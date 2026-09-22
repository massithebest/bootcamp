/** Runtime composition from assistant-ui elements/edit-message. 저장하면 새 분기가 생기고 기존 대화는 이전 버전으로 남는다. */
import type { ReactNode } from "react";
import { ComposerPrimitive, useAuiState } from "@assistant-ui/react";
import { InfoIcon } from "lucide-react";

export function EditMessage({ children }: { children: ReactNode }) {
  const laterReplies = useAuiState((s) => s.thread.messages.slice(s.message.index + 1).filter((m) => m.role === "assistant").length);
  return (
    <ComposerPrimitive.Root data-slot="edit-message" className="ml-auto flex w-full max-w-[85%] flex-col gap-3 rounded border border-accent bg-surface p-3">
      {children}
      {laterReplies > 0 && (
        <p role="note" className="flex items-start gap-2 text-2xs text-ink-2">
          <InfoIcon aria-hidden className="size-3.5 shrink-0" />
          <span>다시 실행하면 새 버전이 만들어지고 지금의 이후 대화(답변 {laterReplies}개)는 이전 버전으로 남습니다. 이 브라우저 세션 동안 버전 이동으로 되돌아갈 수 있습니다.</span>
        </p>
      )}
      <div className="flex justify-end gap-2">
        <ComposerPrimitive.Cancel className="rounded px-2 py-1 text-2xs text-ink-2 hover:bg-surface-2">취소</ComposerPrimitive.Cancel>
        <ComposerPrimitive.Send className="rounded bg-accent px-2 py-1 text-2xs text-accent-ink disabled:opacity-40">저장하고 다시 실행</ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  );
}
