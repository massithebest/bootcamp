/**
 * assistant-ui `ThreadPrimitive.Messages` 에 등록하는 메시지별 컴포넌트.
 *
 * 기존 `message-bubble.tsx` 의 마크업을 최대한 그대로 옮긴다 — 사용자 메시지는
 * 오른쪽 정렬 원문, 어시스턴트 메시지는 진행 블록 위 + 파트 도착 순서 렌더.
 * 도메인 렌더러(`AgentProgress`, `ToolResultCard`)는 무수정으로 재사용한다.
 */

import {
  MessagePrimitive,
  MessagePartPrimitive,
  useAuiState,
  type ToolCallMessagePartProps,
} from "@assistant-ui/react";

import type { ToolResult } from "@/types/chat";
import { AgentProgress } from "./agent-progress";
import { MarkdownText } from "./markdown-text";
import { ToolResultCard } from "./tool-result-card";
import { readAgentMetadata } from "@/lib/chat-runtime";

export function UserMessage() {
  const text = useAuiState((s) => {
    if (s.message.role !== "user") return "";
    const first = s.message.content[0];
    return first && first.type === "text" ? first.text : "";
  });

  return (
    <MessagePrimitive.Root>
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded border border-line-strong bg-surface px-3 py-2 text-ui text-ink">
          {text}
        </div>
      </div>
    </MessagePrimitive.Root>
  );
}

export function AssistantMessage() {
  // 진행 블록(statuses)은 표준 content part 유니온에 대응물이 없어
  // metadata.custom 으로 실어 보낸다 (lib/chat-runtime.ts 참고).
  const metaCustom = useAuiState((s) =>
    s.message.role === "assistant" ? s.message.metadata.custom : undefined,
  );
  const hasContent = useAuiState((s) => s.message.content.length > 0);
  const meta = readAgentMetadata(metaCustom);

  const showThinking =
    Boolean(meta?.streaming) &&
    !hasContent &&
    (meta?.statuses.length ?? 0) === 0 &&
    !meta?.error;

  return (
    <MessagePrimitive.Root>
      <div className="flex flex-col gap-3">
        {meta && (meta.statuses.length > 0 || meta.streaming) && (
          <AgentProgress statuses={meta.statuses} streaming={meta.streaming} />
        )}

        <MessagePrimitive.Parts
          components={{
            Text: AssistantText,
            tools: { Override: ToolPart },
          }}
        />

        {showThinking && (
          <p className="text-ui text-ink-3">응답을 준비하고 있습니다…</p>
        )}

        {meta?.error && (
          <div className="border-l-2 border-block-ink bg-block-weak px-3 py-2 text-ui text-block-ink">
            {meta.error}
          </div>
        )}
      </div>
    </MessagePrimitive.Root>
  );
}

/**
 * 텍스트 파트 렌더러. `MessagePartPrimitive.InProgress` 가 "이 파트가 현재
 * 스트리밍 중인 마지막 파트인지" 를 판정해준다(assistant-ui 의 auto-status —
 * 메시지가 running 이면 마지막 파트만 running). 기존 `lastTextId` 수동 계산을
 * 대체한다.
 */
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

/**
 * 툴 파트 렌더러. `ToolResult` 객체를 통째로 실어 보냈으므로(chat-runtime.ts)
 * `ToolResultCard` 의 props 를 그대로 쓴다 — 그 안의 `tool_name`/`data.kind`
 * 분기는 무수정.
 */
function ToolPart(props: ToolCallMessagePartProps) {
  const result = props.result as ToolResult | undefined;
  if (!result) return null;
  return (
    <div className="border-t border-line pt-3">
      <ToolResultCard result={result} />
    </div>
  );
}
