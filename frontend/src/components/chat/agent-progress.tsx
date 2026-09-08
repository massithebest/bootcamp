/**
 * 에이전트가 도구를 호출하는 과정. 이 제품의 핵심 — 답변과 같은 위계로 응답에 붙되,
 * 완료 후에는 접혀서 밀도를 유지한다. 진행 중에는 펼쳐진다.
 */

"use client";

import { useEffect, useState } from "react";

import type { StatusStep, StepStatus } from "@/types/chat";
import { Chevron, StatusDot, type Tone } from "./primitives";

const STEP_TONE: Record<StepStatus, Tone> = {
  pending: "neutral",
  running: "accent",
  completed: "ok",
  error: "block",
};

const STEP_WORD: Record<StepStatus, string> = {
  pending: "대기",
  running: "진행",
  completed: "완료",
  error: "오류",
};

export function AgentProgress({
  statuses,
  streaming,
}: {
  statuses: StatusStep[];
  streaming: boolean;
}) {
  const running = statuses.find((s) => s.status === "running");
  const hasError = statuses.some((s) => s.status === "error");
  const active = streaming && (Boolean(running) || statuses.length === 0);

  // 진행 중에는 펼침, 완료되면 접힘. 사용자가 직접 토글하면 그 값을 유지.
  const [open, setOpen] = useState(active);
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (!touched) setOpen(active);
  }, [active, touched]);

  if (statuses.length === 0 && !active) return null;

  const summary = running
    ? `${running.label} 중…`
    : hasError
      ? "일부 도구 실행에 실패했습니다"
      : `도구 ${statuses.length}단계 실행`;

  return (
    <div className="rounded border border-line bg-surface/60">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => !v);
          setTouched(true);
        }}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left"
      >
        <Chevron open={open} />
        <StatusDot
          tone={hasError ? "block" : active ? "accent" : "ok"}
          pulse={active}
        />
        <span className="flex-1 text-2xs font-medium text-ink-2">
          {summary}
        </span>
        {!active && !hasError && statuses.length > 0 && (
          <span className="text-2xs text-ink-3">근거 보기</span>
        )}
      </button>

      {open && statuses.length > 0 && (
        <ol className="border-t border-line px-2.5 py-2">
          {statuses.map((s) => (
            <li
              key={s.step}
              className="flex items-center gap-2 py-[3px] text-2xs"
            >
              <StatusDot
                tone={STEP_TONE[s.status]}
                pulse={s.status === "running"}
              />
              <span
                className={
                  s.status === "pending" ? "text-ink-3" : "text-ink-2"
                }
              >
                {s.label}
              </span>
              <span className="ml-auto font-mono text-[0.625rem] text-ink-3">
                {STEP_WORD[s.status]}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
