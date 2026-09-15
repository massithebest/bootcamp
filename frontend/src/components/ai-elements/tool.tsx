import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import {
  CheckCircleIcon,
  ChevronDownIcon,
  CircleIcon,
  ClockIcon,
  WrenchIcon,
  XCircleIcon,
} from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

// AI Elements `tool` 원본에서 code-block(shiki) 의존과 ToolInput을 제거하고
// 색/라벨을 프로젝트 토큰·한국어로 맞춘 버전. 상태 값은 ai SDK ToolUIPart 계약을 따른다.

export type ToolProps = ComponentProps<typeof Collapsible>;

export const Tool = ({ className, ...props }: ToolProps) => (
  <Collapsible
    className={cn("group not-prose w-full", className)}
    {...props}
  />
);

/**
 * Vercel AI SDK(`ai`)의 `ToolUIPart` / `DynamicToolUIPart` 계약 중
 * 이 컴포넌트가 실제로 쓰는 표면(`type`, `state`)만 옮겨 온 것.
 * 타입 3개 때문에 `ai` + `@ai-sdk/*` 트리(~12.6MB, `@ai-sdk/gateway`에
 * `https://ai-gateway.vercel.sh` 하드코딩)를 폐쇄망 반입 대상에 넣지 않기 위함.
 * 원본 계약이 바뀌면 이 블록만 맞추면 된다.
 */
type ToolUIPartType = `tool-${string}`;
type DynamicToolUIPartType = "dynamic-tool";

type ToolUIPartState =
  | "input-streaming"
  | "input-available"
  | "approval-requested"
  | "approval-responded"
  | "output-available"
  | "output-error"
  | "output-denied";

export type ToolPart =
  | { type: ToolUIPartType; state: ToolUIPartState }
  | { type: DynamicToolUIPartType; state: ToolUIPartState };
export type ToolState = ToolPart["state"];

export type ToolHeaderProps = {
  title?: string;
  className?: string;
} & (
  | { type: ToolUIPartType; state: ToolState; toolName?: never }
  | { type: DynamicToolUIPartType; state: ToolState; toolName: string }
);

const statusLabels: Record<ToolState, string> = {
  "approval-requested": "승인 대기",
  "approval-responded": "응답됨",
  "input-available": "실행 중",
  "input-streaming": "대기",
  "output-available": "완료",
  "output-denied": "거부됨",
  "output-error": "오류",
};

const statusIcons: Record<ToolState, ReactNode> = {
  "approval-requested": <ClockIcon className="size-3.5 text-warn-ink" />,
  "approval-responded": <CheckCircleIcon className="size-3.5 text-accent" />,
  "input-available": (
    <ClockIcon className="size-3.5 text-accent motion-safe:animate-pulse" />
  ),
  "input-streaming": <CircleIcon className="size-3.5 text-ink-3" />,
  "output-available": <CheckCircleIcon className="size-3.5 text-ok-ink" />,
  "output-denied": <XCircleIcon className="size-3.5 text-warn-ink" />,
  "output-error": <XCircleIcon className="size-3.5 text-block-ink" />,
};

const getStatusBadge = (status: ToolState) => (
  <span className="inline-flex items-center gap-1 text-2xs text-ink-3">
    {statusIcons[status]}
    {statusLabels[status]}
  </span>
);

export const ToolHeader = ({
  className,
  title,
  type,
  state,
  toolName,
  ...props
}: ToolHeaderProps) => {
  const derivedName =
    type === "dynamic-tool" ? toolName : type.split("-").slice(1).join("-");

  return (
    <CollapsibleTrigger
      className={cn(
        "flex w-full items-center justify-between gap-3 py-1 text-left",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 items-baseline gap-2">
        <WrenchIcon className="size-3.5 shrink-0 translate-y-[2px] text-ink-3" />
        <span className="text-2xs font-semibold text-ink-2">
          {title ?? derivedName}
        </span>
        <span className="truncate font-mono text-2xs text-ink-3">
          {derivedName}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {getStatusBadge(state)}
        <ChevronDownIcon className="size-3.5 text-ink-3 transition-transform group-data-[state=open]:rotate-180 group-data-[panel-open]:rotate-180" />
      </div>
    </CollapsibleTrigger>
  );
};

export type ToolContentProps = ComponentProps<typeof CollapsibleContent>;

export const ToolContent = ({ className, ...props }: ToolContentProps) => (
  <CollapsibleContent className={cn("pt-2", className)} {...props} />
);

export type ToolOutputProps = ComponentProps<"div"> & {
  output?: ReactNode;
  errorText?: string | null;
};

export const ToolOutput = ({
  className,
  output,
  errorText,
  ...props
}: ToolOutputProps) => {
  if (!output && !errorText) return null;

  return (
    <div className={cn("flex flex-col gap-2", className)} {...props}>
      {errorText && (
        <div className="border-l-2 border-block-ink bg-block-weak px-3 py-2 text-ui text-block-ink">
          {errorText}
        </div>
      )}
      {output}
    </div>
  );
};
