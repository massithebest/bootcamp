/**
 * 대화 시작 전 빈 상태.  이 도구로 무엇을 물어볼 수 있는지 실제 생산계획 용어로.
 */

"use client";

import { EXAMPLE_QUESTIONS } from "@/lib/dummy";

export function EmptyState({
  onPick,
}: {
  onPick: (question: string) => void;
}) {
  return (
    <div className="mx-auto flex max-w-reading flex-col gap-5 py-14">
      <div>
        <h2 className="text-ui-lg font-semibold text-ink">
          무엇을 검토할까요?
        </h2>
        <p className="mt-1 text-ui leading-relaxed text-ink-2">
          생산 실적 조회, 공정 문서 검색, 라인·자재·비교 시뮬레이션을 조합해
          답변합니다. 근거가 되는 데이터와 수치를 함께 제시합니다.
        </p>
      </div>

      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {EXAMPLE_QUESTIONS.map((q) => (
          <li key={q}>
            <button
              type="button"
              onClick={() => onPick(q)}
              className="w-full py-2.5 text-left text-ui text-ink-2 transition-colors hover:text-ink"
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
