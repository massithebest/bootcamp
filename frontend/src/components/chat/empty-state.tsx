/**
 * 대화 시작 전 빈 상태.  이 도구로 무엇을 물어볼 수 있는지 실제 생산계획 용어로.
 *
 * 예시 질문은 App의 정적 Suggestions scope에서 읽고 런타임에 직접 전송한다.
 */

import { SuggestionPrimitive, ThreadPrimitive } from "@assistant-ui/react";

export function EmptyState() {
  return (
    <div className="text-center">
      <h2 className="text-2xl font-semibold tracking-tight text-ink">
        무엇을 도와드릴까요?
      </h2>
      <p className="mt-2 text-ui leading-relaxed text-ink-2">
        생산계획 데이터 조회부터 계획 수립 과정과 운영 기준까지 확인해 보세요.
      </p>
    </div>
  );
}

export function ExampleSuggestions() {
  return (
    <ul className="flex max-w-[42rem] flex-wrap justify-center gap-2">
      <ThreadPrimitive.Suggestions>
        {() => (
          <li>
            <SuggestionPrimitive.Trigger
              send
              className="rounded-md border border-line-strong bg-canvas px-3 py-1.5 text-ui text-ink-2 transition-colors hover:bg-surface hover:text-ink"
            >
              <SuggestionPrimitive.Title />
            </SuggestionPrimitive.Trigger>
          </li>
        )}
      </ThreadPrimitive.Suggestions>
    </ul>
  );
}
