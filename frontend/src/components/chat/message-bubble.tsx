/**
 * 사용자 / 에이전트 메시지 표현.
 *   사용자 → 오른쪽, 톤 낮춤    에이전트 → 왼쪽, 읽기 컬럼 전체 폭
 *
 * 에이전트 응답:  접이식 진행 블록(위) → 도착 순서대로 [서술 텍스트 / 도구 결과].
 * 텍스트는 Markdown 뷰어로 렌더한다 (원문 노출 X).
 */

import type { ChatMessage } from "@/types/chat";
import { AgentProgress } from "./agent-progress";
import { Markdown } from "./markdown";
import { ToolResultCard } from "./tool-result-card";

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded border border-line-strong bg-surface px-3 py-2 text-ui text-ink">
          {message.content}
        </div>
      </div>
    );
  }

  const lastTextId = [...message.parts]
    .reverse()
    .find((p) => p.kind === "text")?.id;

  const showThinking =
    message.streaming &&
    message.parts.length === 0 &&
    message.statuses.length === 0 &&
    !message.error;

  return (
    <div className="flex flex-col gap-3">
      {(message.statuses.length > 0 || message.streaming) && (
        <AgentProgress
          statuses={message.statuses}
          streaming={message.streaming}
        />
      )}

      {message.parts.map((part) =>
        part.kind === "text" ? (
          <div
            key={part.id}
            className="text-ui-lg leading-[1.6] text-ink"
          >
            <Markdown text={part.text} />
            {message.streaming && part.id === lastTextId && (
              <span className="ml-0.5 inline-block h-3.5 w-[2px] translate-y-[2px] bg-accent motion-safe:animate-pulse" />
            )}
          </div>
        ) : (
          <div
            key={part.id}
            className="border-t border-line pt-3"
          >
            <ToolResultCard result={part.result} />
          </div>
        ),
      )}

      {showThinking && (
        <p className="text-ui text-ink-3">응답을 준비하고 있습니다…</p>
      )}

      {message.error && (
        <div className="border-l-2 border-block-ink bg-block-weak px-3 py-2 text-ui text-block-ink">
          {message.error}
        </div>
      )}
    </div>
  );
}
