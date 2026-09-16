/** Adapted from assistant-ui elements-agent-plan. Explicit states avoid inferring completion. */
import { AlertCircleIcon, CheckIcon, CircleIcon, LoaderIcon, SquareIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { mono } from "./surfaces";

export interface PlanStep {
  id: string;
  label: string;
  detail?: string;
  status: "pending" | "running" | "completed" | "error" | "stopped" | "unknown";
}

const STATES = {
  pending: { Icon: CircleIcon, label: "대기", color: "text-ink-3" },
  running: { Icon: LoaderIcon, label: "진행", color: "text-accent" },
  completed: { Icon: CheckIcon, label: "완료", color: "text-ok-ink" },
  error: { Icon: AlertCircleIcon, label: "오류", color: "text-block-ink" },
  stopped: { Icon: SquareIcon, label: "중단", color: "text-ink-3" },
  unknown: { Icon: CircleIcon, label: "완료 미확인", color: "text-ink-3" },
};

export function AgentPlan({ steps }: { steps: readonly PlanStep[] }) {
  const completed = steps.filter((s) => s.status === "completed").length;
  return (
    <div data-slot="agent-plan" className="flex w-full flex-col gap-3">
      <div className="flex items-center justify-between text-2xs text-ink-2">
        <span>실행 단계</span><span className={mono}>{completed} / {steps.length} 완료</span>
      </div>
      <div role="progressbar" aria-label="실행 단계 완료" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={Math.max(steps.length, 1)} className="h-0.5 overflow-hidden rounded bg-surface-2">
        <span className="block h-full bg-accent transition-[width] motion-reduce:transition-none" style={{ width: `${steps.length ? completed / steps.length * 100 : 0}%` }} />
      </div>
      <ul className="flex flex-col gap-2">
        {steps.map((step) => {
          const { Icon, label, color } = STATES[step.status];
          return (
            <li key={step.id} className="flex items-start gap-2 text-ui">
              <Icon aria-hidden className={cn("mt-0.5 size-4 shrink-0", color, step.status === "running" && "motion-safe:animate-spin")} />
              <span className="min-w-0 flex-1 text-ink">{step.label}{step.detail && step.detail !== step.label && <span className="ml-2 text-ink-2">{step.detail}</span>}</span>
              <span className={cn("text-2xs", color)}>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
