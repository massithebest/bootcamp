/**
 * 사용자 입력. `ComposerPrimitive` 로 구현한다 — 전송/Enter 처리/자동 높이/
 * 실행 중 비활성/취소 버튼을 라이브러리가 담당한다(Q4: onCancel 은 1단계에서
 * 이미 기존 AbortController 기반 handleStop 에 연결됨, chat-window.tsx 참고).
 *
 * 기존 마크업·스타일은 그대로 유지한다. `disabled`/`onSend` prop 은 더 이상
 * 필요 없다 — 스트리밍 여부·전송은 런타임이 소유한다.
 */

import { SquareIcon } from "lucide-react";

import { AuiIf, ComposerPrimitive } from "@assistant-ui/react";

export function MessageInput() {
  return (
    <ComposerPrimitive.Root className="border-t border-line bg-canvas px-4 py-3">
      <div className="mx-auto flex max-w-reading items-end gap-2">
        <div className="flex flex-1 flex-col rounded border border-line-strong bg-canvas focus-within:border-accent">
          <ComposerPrimitive.Input
            rows={1}
            placeholder="생산계획에 대해 질문하세요. 예: 9월 A라인에서 KRA-1180 1,000개 가능한가?"
            className="max-h-44 resize-none bg-transparent px-3 py-2 text-ui text-ink outline-none placeholder:text-ink-3 disabled:opacity-60"
          />
          <div className="px-3 pb-1.5 text-[0.625rem] text-ink-3">
            Enter 전송 · Shift+Enter 줄바꿈
          </div>
        </div>

        <AuiIf condition={(s) => s.thread.isRunning}>
          <ComposerPrimitive.Cancel
            className="grid h-9 w-9 shrink-0 place-items-center rounded border border-line-strong text-ink-2 transition-colors hover:bg-surface-2"
            aria-label="중단"
          >
            <SquareIcon className="size-3.5" fill="currentColor" />
          </ComposerPrimitive.Cancel>
        </AuiIf>
        <AuiIf condition={(s) => !s.thread.isRunning}>
          <ComposerPrimitive.Send className="h-9 shrink-0 rounded bg-accent px-3.5 text-ui font-medium text-accent-ink transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-ink-3">
            전송
          </ComposerPrimitive.Send>
        </AuiIf>
      </div>
    </ComposerPrimitive.Root>
  );
}
