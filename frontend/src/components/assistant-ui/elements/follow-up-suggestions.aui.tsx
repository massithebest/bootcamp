"use client";

import { AuiIf, ThreadPrimitive, useAuiState } from "@assistant-ui/react";
import type { FC } from "react";

/**
 * 성공한 응답 뒤의 후속질문. 값은 Backend가 보낸 검증된 `done.data.suggestions`이며,
 * 없거나 오류·취소·실행 중이면 표시하지 않는다. 클릭하면 바로 전송한다.
 */
const FollowupSuggestionsRow: FC = () => {
  const suggestions = useAuiState((s) => s.thread.suggestions);
  return (
    <ul
      aria-label="후속 질문 제안"
      data-slot="followup-suggestions"
      className="flex flex-wrap gap-2 pb-2"
    >
      {suggestions.map((suggestion) => (
        <li key={suggestion.prompt}>
          <ThreadPrimitive.Suggestion
            prompt={suggestion.prompt}
            send
            className="rounded-md border border-line-strong bg-canvas px-3 py-1.5 text-left text-ui text-ink-2 transition-colors hover:bg-surface hover:text-ink"
          >
            {suggestion.title ?? suggestion.prompt}
          </ThreadPrimitive.Suggestion>
        </li>
      ))}
    </ul>
  );
};

export const ThreadFollowupSuggestions: FC = () => (
  <AuiIf
    condition={(s) =>
      !s.thread.isEmpty && !s.thread.isRunning && s.thread.suggestions.length > 0
    }
  >
    <FollowupSuggestionsRow />
  </AuiIf>
);
