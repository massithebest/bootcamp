/** Production-planning extension for the assistant-ui Thread AssistantMessage slot. */
import { useEffect, useState, type ReactNode } from "react";
import { LoaderIcon } from "lucide-react";
import {
  MessagePrimitive,
  MessagePartPrimitive,
  groupPartByType,
  useAuiState,
  type ToolCallMessagePartProps,
} from "@assistant-ui/react";

import {
  AgentPlan,
  type PlanStep,
} from "@/components/assistant-ui/elements/agent-plan";
import { MessageActions, MessageError } from "@/components/assistant-ui/elements/message-actions.aui";
import { MarkdownText } from "@/components/assistant-ui/elements/markdown-text";
import { StoppedRun } from "@/components/assistant-ui/elements/stopped-run.aui";
import {
  ToolGroupContent,
  ToolGroupRoot,
  ToolGroupTrigger,
} from "@/components/assistant-ui/elements/tool-group.aui";
import { readAgentMetadata } from "@/lib/chat-runtime";
import type { StatusStep, ToolResult } from "@/types/chat";
import { ToolResultCard } from "./tool-result-card";

const groupMessageParts = groupPartByType({
  "tool-call": ["group-tool"],
  "standalone-tool-call": [],
});

export function AssistantMessage() {
  const hasToolParts = useAuiState((s) =>
    s.message.parts.some((part) => part.type === "tool-call"),
  );
  const hasTextParts = useAuiState((s) =>
    s.message.parts.some((part) => part.type === "text"),
  );
  const messageRunning = useAuiState((s) => s.message.status?.type === "running");
  const customMetadata = useAuiState((s) => s.message.metadata.custom);
  const publicStatuses = readAgentMetadata(customMetadata)?.statuses ?? [];

  return (
    <MessagePrimitive.Root data-role="assistant" className="min-w-0">
      <div className="flex flex-col gap-3">
        {!hasToolParts && (
          <StandaloneExecution
            running={messageRunning}
            writing={hasTextParts}
            statuses={publicStatuses}
          />
        )}

        <MessagePrimitive.GroupedParts groupBy={groupMessageParts} indicator="never">
          {({ part, children }) => {
            switch (part.type) {
              case "group-tool":
                return (
                  <ExecutionToolGroup
                    count={part.indices.length}
                    toolRunning={part.status.type === "running"}
                    statuses={publicStatuses}
                  >
                    {children}
                  </ExecutionToolGroup>
                );
              case "text":
                return <AssistantText />;
              case "tool-call":
                return part.toolUI ?? <ToolPart {...part} />;
              default:
                return null;
            }
          }}
        </MessagePrimitive.GroupedParts>

        <StoppedRun />
        <MessageError />
        <MessageActions />
      </div>
    </MessagePrimitive.Root>
  );
}

/** Immediate feedback while the backend/model is preparing its first public Tool call. */
function PendingExecution({ writing }: { writing: boolean }) {
  return (
    <div role="status" className="flex items-center gap-2 py-1.5 text-xs text-ink-3">
      <LoaderIcon aria-hidden className="size-3 animate-spin [animation-duration:0.6s]" />
      <span className="shimmer motion-reduce:animate-none">
        {writing ? "응답 작성 중" : "요청 분석 중"}
      </span>
    </div>
  );
}

/**
 * 실행 중에는 펼쳐 두어 진행 상황을 보여주고, 최종 응답이 확정되면 전체
 * Tool 목록을 접는다. 이후에는 사용자가 원하는 단계까지만 다시 펼칠 수 있다.
 */
function ExecutionToolGroup({
  count,
  toolRunning,
  statuses,
  children,
}: {
  count: number;
  toolRunning: boolean;
  statuses: readonly StatusStep[];
  children: ReactNode;
}) {
  const messageStatus = useAuiState((s) => s.message.status);
  const messageRunning = messageStatus?.type === "running";
  const isComplete = messageStatus?.type === "complete";
  const isFailed = messageStatus?.type === "incomplete" && messageStatus.reason === "error";
  const isCancelled = messageStatus?.type === "incomplete" && messageStatus.reason === "cancelled";
  const [open, setOpen] = useState(messageRunning);

  useEffect(() => {
    setOpen(messageRunning);
  }, [messageRunning]);

  let label = `응답 작성 완료 · 툴 ${count}개 사용`;
  if (toolRunning && messageRunning) label = `툴 ${count}개 실행 중`;
  else if (messageRunning) label = `응답 작성 중 · 툴 ${count}개 사용`;
  else if (isFailed) label = `툴 ${count}개 사용 · 오류`;
  else if (isCancelled) label = `툴 ${count}개 사용 · 중단`;

  return (
    <ToolGroupRoot
      variant="ghost"
      open={open}
      onOpenChange={setOpen}
      className="max-w-full"
    >
      <ToolGroupTrigger
        count={count}
        active={messageRunning}
        completed={isComplete}
        label={label}
      />
      <ToolGroupContent aria-busy={messageRunning}>
        {statuses.length > 0 && (
          <AgentPlan steps={toPlanSteps(statuses, messageRunning, isFailed, isCancelled)} />
        )}
        {children}
      </ToolGroupContent>
    </ToolGroupRoot>
  );
}

/** Tool 호출과 별개로 Backend가 공개한 업무 진행 단계를 같은 실행 과정에 둔다. */
function StandaloneExecution({
  running,
  writing,
  statuses,
}: {
  running: boolean;
  writing: boolean;
  statuses: readonly StatusStep[];
}) {
  const messageStatus = useAuiState((s) => s.message.status);
  const isComplete = messageStatus?.type === "complete";
  const isFailed = messageStatus?.type === "incomplete" && messageStatus.reason === "error";
  const isCancelled = messageStatus?.type === "incomplete" && messageStatus.reason === "cancelled";
  const [open, setOpen] = useState(running);

  useEffect(() => {
    setOpen(running);
  }, [running]);

  if (statuses.length === 0) return running ? <PendingExecution writing={writing} /> : null;

  const hasRunningStatus = statuses.some((step) => step.status === "running");
  let label = "응답 작성 완료";
  if (running && hasRunningStatus) label = "실행 과정 진행 중";
  else if (running) label = "응답 작성 중";
  else if (isFailed) label = "실행 과정 · 오류";
  else if (isCancelled) label = "실행 과정 · 중단";

  return (
    <ToolGroupRoot
      variant="ghost"
      open={open}
      onOpenChange={setOpen}
      className="max-w-full"
    >
      <ToolGroupTrigger
        count={0}
        active={running}
        completed={isComplete}
        label={label}
      />
      <ToolGroupContent aria-busy={running}>
        <AgentPlan steps={toPlanSteps(statuses, running, isFailed, isCancelled)} />
      </ToolGroupContent>
    </ToolGroupRoot>
  );
}

function toPlanSteps(
  statuses: readonly StatusStep[],
  messageRunning: boolean,
  failed: boolean,
  cancelled: boolean,
): PlanStep[] {
  return statuses.map((step) => {
    let status: PlanStep["status"] = step.status;
    if (!messageRunning && (status === "pending" || status === "running")) {
      status = cancelled ? "stopped" : failed ? "error" : "unknown";
    }
    return {
      id: step.step,
      label: step.label,
      detail: step.detail,
      status,
    };
  });
}

/** assistant text with a small streaming cursor on the current part. */
function AssistantText() {
  return (
    <div className="text-ui-lg leading-[1.6] text-ink">
      <MarkdownText />
      <MessagePartPrimitive.InProgress>
        <span className="ml-0.5 inline-block h-3.5 w-[2px] translate-y-[2px] bg-accent motion-safe:animate-pulse" />
      </MessagePartPrimitive.InProgress>
    </div>
  );
}

/** A second disclosure level for one tool's public parameters and result. */
function ToolPart(props: ToolCallMessagePartProps) {
  const result = props.result as ToolResult | undefined;
  const args = isRecord(props.args) ? props.args : {};
  const messageRunning = useAuiState((s) => s.message.status?.type === "running");

  return (
    <ToolResultCard
      toolName={props.toolName}
      args={args}
      result={result}
      running={props.status.type === "running"}
      messageRunning={messageRunning}
    />
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
