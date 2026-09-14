/**
 * 에이전트가 도구를 호출하는 과정. 이 제품의 핵심 — 답변과 같은 위계로 응답에 붙되,
 * 완료 후에는 접혀서 밀도를 유지한다. 진행 중에는 펼쳐진다.
 * 마크업은 AI Elements `ChainOfThought`, 펼침 상태는 여기서 소유한다.
 */

"use client";

import { useEffect, useState } from "react";
import {
  AlertCircleIcon,
  CheckIcon,
  CircleIcon,
  LoaderIcon,
  type LucideIcon,
} from "lucide-react";

import type { StatusStep, StepStatus } from "@/types/chat";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
  type StepIcon,
} from "@/components/ai-elements/chain-of-thought";
import { StatusDot } from "./primitives";

type CotStatus = "complete" | "active" | "pending";

// ChainOfThoughtStep 은 icon 에 고정 className 을 주므로, 색은 아이콘 쪽에서 미리 입힌다.
const tinted = (Icon: LucideIcon, cls: string): StepIcon => {
  const Tinted = () => <Icon className={`size-3.5 ${cls}`} />;
  Tinted.displayName = `Tinted(${Icon.displayName ?? "Icon"})`;
  return Tinted;
};

const STEP_VIEW: Record<
  StepStatus,
  { status: CotStatus; icon: StepIcon; word: string }
> = {
  pending: { status: "pending", icon: tinted(CircleIcon, "text-ink-3"), word: "대기" },
  running: {
    status: "active",
    icon: tinted(LoaderIcon, "text-accent motion-safe:animate-spin"),
    word: "진행",
  },
  completed: { status: "complete", icon: tinted(CheckIcon, "text-ok-ink"), word: "완료" },
  error: {
    status: "complete",
    icon: tinted(AlertCircleIcon, "text-block-ink"),
    word: "오류",
  },
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
    <ChainOfThought
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        setTouched(true);
      }}
      className="space-y-0 rounded border border-line bg-surface/60"
    >
      <ChainOfThoughtHeader className="gap-2 px-2.5 py-1.5 text-2xs font-medium text-ink-2 hover:text-ink [&>svg:first-child]:hidden">
        <span className="flex items-center gap-2">
          <StatusDot
            tone={hasError ? "block" : active ? "accent" : "ok"}
            pulse={active}
          />
          {summary}
          {!active && !hasError && statuses.length > 0 && (
            <span className="font-normal text-ink-3">근거 보기</span>
          )}
        </span>
      </ChainOfThoughtHeader>

      {statuses.length > 0 && (
        <ChainOfThoughtContent className="mt-0 space-y-1 border-t border-line px-2.5 py-2">
          {statuses.map((s) => {
            const view = STEP_VIEW[s.status];
            return (
              <ChainOfThoughtStep
                key={s.step}
                status={view.status}
                icon={view.icon}
                label={
                  <span className="flex items-center gap-2 text-2xs">
                    <span className={s.status === "pending" ? "text-ink-3" : "text-ink-2"}>
                      {s.label}
                    </span>
                    <span className="ml-auto font-mono text-[0.625rem] text-ink-3">
                      {view.word}
                    </span>
                  </span>
                }
                className="gap-2 text-2xs [&>div:first-child>div]:hidden"
              />
            );
          })}
        </ChainOfThoughtContent>
      )}
    </ChainOfThought>
  );
}
