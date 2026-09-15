/**
 * assistant-ui `ThreadPrimitive.Messages` children renderer가 선택하는 메시지 컴포넌트.
 *
 * 기존 `message-bubble.tsx` 의 마크업을 최대한 그대로 옮긴다 — 사용자 메시지는
 * 오른쪽 정렬 원문, 어시스턴트 메시지는 진행 블록 위 + 파트 도착 순서 렌더.
 * 도메인 렌더러(`AgentProgress`, `ToolResultCard`)는 무수정으로 재사용한다.
 */

import { CheckIcon, CopyIcon, PencilIcon, RotateCcwIcon } from "lucide-react";

import {
  ActionBarPrimitive,
  ComposerPrimitive,
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
  return (
    <MessagePrimitive.Root>
      <div className="flex flex-col items-end gap-1">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded border border-line-strong bg-surface px-3 py-2 text-ui text-ink">
          <MessagePrimitive.Parts>
            {({ part }) =>
              part.type === "text" ? <MessagePartPrimitive.Text /> : null
            }
          </MessagePrimitive.Parts>
        </div>
        <ActionBarPrimitive.Root
          hideWhenRunning
          autohide="not-last"
          className="flex items-center"
        >
          <ActionBarPrimitive.Edit className="inline-flex items-center gap-1 rounded px-1.5 py-1 text-2xs text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink-2 disabled:pointer-events-none disabled:opacity-0">
            <PencilIcon className="size-3" /> 편집
          </ActionBarPrimitive.Edit>
        </ActionBarPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  );
}

/**
 * 사용자 메시지 편집 모드. `ActionBarPrimitive.Edit` 클릭 시
 * `ThreadPrimitive.Messages` 의 `UserEditComposer` 슬롯으로 교체 렌더된다.
 * `ComposerPrimitive` 는 편집 컨텍스트에서도 그대로 동작한다 — 현재 텍스트로
 * 미리 채워지고, Send 는 onEdit(편집 저장 + 포크 재실행)을 부른다.
 */
export function UserEditComposer() {
  return (
    <div className="flex justify-end">
      <ComposerPrimitive.Root className="flex w-full max-w-[85%] flex-col gap-1.5 rounded border border-accent bg-surface px-3 py-2">
        <ComposerPrimitive.Input
          className="resize-none bg-transparent text-ui text-ink outline-none"
          autoFocus
        />
        <div className="flex justify-end gap-1.5">
          <ComposerPrimitive.Cancel className="rounded px-2 py-1 text-2xs text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink-2">
            취소
          </ComposerPrimitive.Cancel>
          <ComposerPrimitive.Send className="rounded bg-accent px-2.5 py-1 text-2xs font-medium text-accent-ink transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-ink-3">
            저장하고 다시 실행
          </ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.Root>
    </div>
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

        <MessagePrimitive.Parts>
          {({ part }) => {
            if (part.type === "text") return <AssistantText />;
            if (part.type === "tool-call") {
              return part.toolUI ?? <ToolPart {...part} />;
            }
            return null;
          }}
        </MessagePrimitive.Parts>

        {showThinking && (
          <p className="text-ui text-ink-3">응답을 준비하고 있습니다…</p>
        )}

        {meta?.error && (
          <div className="border-l-2 border-block-ink bg-block-weak px-3 py-2 text-ui text-block-ink">
            {meta.error}
          </div>
        )}

        <ActionBarPrimitive.Root
          hideWhenRunning
          autohide="not-last"
          autohideFloat="single-branch"
          className="flex items-center gap-1"
        >
          <CopyButton />
          <ActionBarPrimitive.Reload className="inline-flex items-center gap-1 rounded px-1.5 py-1 text-2xs text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink-2 disabled:pointer-events-none disabled:opacity-0">
            <RotateCcwIcon className="size-3" /> 재생성
          </ActionBarPrimitive.Reload>
        </ActionBarPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  );
}

/** 복사 버튼. `data-copied` 대신 `message.isCopied` 를 직접 읽어 아이콘/라벨을 바꾼다. */
function CopyButton() {
  const isCopied = useAuiState((s) => s.message.isCopied);
  return (
    <ActionBarPrimitive.Copy className="inline-flex items-center gap-1 rounded px-1.5 py-1 text-2xs text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink-2 disabled:pointer-events-none disabled:opacity-0">
      {isCopied ? (
        <>
          <CheckIcon className="size-3" /> 복사됨
        </>
      ) : (
        <>
          <CopyIcon className="size-3" /> 복사
        </>
      )}
    </ActionBarPrimitive.Copy>
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
