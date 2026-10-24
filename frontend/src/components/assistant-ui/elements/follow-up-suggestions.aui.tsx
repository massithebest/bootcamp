"use client";

import { AuiIf, ThreadPrimitive, useAuiState } from "@assistant-ui/react";
import { useMemo, type FC } from "react";

import { branchSuggestions } from "@/lib/agent-threads";

/**
 * 성공한 응답 뒤의 후속질문. 값은 Backend가 보낸 검증된 `done.data.suggestions`이며,
 * 없거나 오류·취소·실행 중이면 표시하지 않는다. 클릭하면 바로 전송한다.
 * 질문 수정으로 버전을 바꾸면 그 분기의 마지막 답변에 실린 질문을 보여준다.
 */
const FollowupSuggestionsRow: FC = () => {
  const last = useAuiState((s) => s.thread.messages.at(-1));
  const suggestions = useMemo(() => branchSuggestions(last), [last]);
  return (
    <ul
      aria-label="후속 질문 제안"
      data-slot="followup-suggestions"
      className="flex flex-wrap gap-2 pb-2"
    >
      {suggestions.map((prompt) => (
        <li key={prompt}>
          <ThreadPrimitive.Suggestion
            prompt={prompt}
            send
            className="rounded-md border border-line-strong bg-canvas px-3 py-1.5 text-left text-ui text-ink-2 transition-colors hover:bg-surface hover:text-ink"
          >
            {prompt}
          </ThreadPrimitive.Suggestion>
        </li>
      ))}
    </ul>
  );
};

export const ThreadFollowupSuggestions: FC = () => (
  <AuiIf
    condition={(s) =>
      !s.thread.isEmpty && !s.thread.isRunning && branchSuggestions(s.thread.messages.at(-1)).length > 0
    }
  >
    <FollowupSuggestionsRow />
  </AuiIf>
);
