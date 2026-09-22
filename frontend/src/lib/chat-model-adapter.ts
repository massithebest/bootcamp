/**
 * assistant-ui LocalRuntime `ChatModelAdapter` — 기존 SSE(`sendChatMessage`)와 순수 상태 전이
 * (`applyAgentEvent`, `convertMessage`)를 그대로 쓰고, 메시지 저장·취소·편집·재생성·분기는 runtime이 맡는다.
 *
 * Backend는 `conversation_id`로 세션을 기억하고 `fork_from_turn_id`로 시작 지점을 정한다.
 * 분기(편집·재생성)에서 어느 지점부터 이어야 하는지는 `planTurn`이 결정한다.
 */
import type { ChatModelAdapter } from "@assistant-ui/react";

import type { AgentEvent, ChatMessage } from "@/types/chat";
import { createConversationId, sendChatMessage } from "@/lib/chat-api";
import { toRunResult } from "@/lib/chat-runtime";
import { applyAgentEvent } from "@/lib/chat-state";
import { EventQueue } from "@/lib/event-queue";

/** thread 하나가 Backend 대화 하나에 대응한다. */
export interface AgentConversation {
  readonly id: string;
  /** Backend가 마지막으로 성공 기록한 turn. 다른 분기에서 이어 쓸 때 fork 필요 여부를 가른다. */
  headTurnId: string | undefined;
}

export function createConversation(id: string = createConversationId()): AgentConversation {
  return { id, headTurnId: undefined };
}

interface PlanMessage {
  readonly role: string;
  readonly content: readonly { readonly type: string; readonly text?: string }[] | string;
  readonly metadata?: { readonly custom?: Readonly<Record<string, unknown>> };
}

export interface TurnPlan {
  text: string;
  /** undefined = 현재 세션 이어쓰기, "" = 처음부터, 그 외 = 해당 turn에서 fork. */
  forkFromTurnId: string | undefined;
}

function textOf(message: PlanMessage): string {
  if (typeof message.content === "string") return message.content.trim();
  return message.content
    .filter((part) => part.type === "text" && typeof part.text === "string")
    .map((part) => part.text)
    .join("")
    .trim();
}

/**
 * runtime이 넘긴 분기 경로(`messages`, 마지막이 보낼 user 메시지)에서 요청을 계산한다.
 *
 * 경로에서 가장 가까운 성공 assistant의 turnId가 anchor다. anchor가 대화의 현재 head와 같으면
 * 평범한 다음 턴이라 fork를 생략하고, 다르면(다른 분기·편집·재생성) anchor에서 fork한다.
 * anchor가 없으면 head가 없을 때만 이어 쓰고, head가 있으면 처음부터 다시 시작한다.
 */
export function planTurn(
  messages: readonly PlanMessage[],
  conversation: Pick<AgentConversation, "headTurnId">,
): TurnPlan | null {
  const last = messages.length - 1;
  if (last < 0 || messages[last].role !== "user") return null;
  const text = textOf(messages[last]);
  if (!text) return null;

  let anchor: string | undefined;
  for (let index = last - 1; index >= 0; index -= 1) {
    const turnId = messages[index].role === "assistant" ? messages[index].metadata?.custom?.turnId : undefined;
    if (typeof turnId === "string" && turnId) {
      anchor = turnId;
      break;
    }
  }
  const head = conversation.headTurnId;
  if (anchor === undefined) return { text, forkFromTurnId: head === undefined ? undefined : "" };
  return { text, forkFromTurnId: anchor === head ? undefined : anchor };
}

export interface AdapterDeps {
  sendChatMessage: typeof sendChatMessage;
  /** 스트림 갱신을 묶는 간격. 백그라운드 탭에서도 멈추지 않도록 timer를 쓴다. */
  frame: () => Promise<void>;
  now: () => number;
}

const defaultDeps: AdapterDeps = {
  sendChatMessage,
  frame: () => new Promise((resolve) => setTimeout(resolve, 16)),
  now: () => performance.now(),
};

let partCounter = 0;
const nextPartId = () => `part-${Date.now()}-${(partCounter += 1)}`;

function emptyAssistant(startedAt: number): ChatMessage {
  return {
    id: "assistant",
    role: "assistant",
    content: "",
    parts: [],
    statuses: [],
    runState: { type: "running" },
    observedTiming: { startedAt },
  };
}

export function createAgentChatAdapter(
  conversation: AgentConversation,
  overrides: Partial<AdapterDeps> = {},
): ChatModelAdapter {
  const deps = { ...defaultDeps, ...overrides };

  return {
    async *run({ messages, abortSignal }) {
      const plan = planTurn(messages, conversation);
      if (!plan) return;

      const queue = new EventQueue<AgentEvent>();
      const onAbort = () => queue.close();
      abortSignal.addEventListener("abort", onAbort, { once: true });
      const request = deps
        .sendChatMessage({
          message: plan.text,
          conversationId: conversation.id,
          forkFromTurnId: plan.forkFromTurnId,
          signal: abortSignal,
          onEvent: (event) => queue.push(event),
        })
        .catch(() => "failed" as const)
        .finally(() => queue.close());

      let message = emptyAssistant(deps.now());
      let finished = false;
      try {
        for await (const batch of queue.batches()) {
          if (abortSignal.aborted) return;
          for (const event of batch) {
            message = applyAgentEvent(message, event, nextPartId(), deps.now());
          }
          // 성공한 turn은 종료 상태를 내보내는 순간 head로 기록한다. 마무리 대기 중에 다음 질문이
          // 시작돼도 fork 판단이 어긋나지 않게 한다.
          const completed = message.runState.type === "complete";
          if (completed && message.turnId) conversation.headTurnId = message.turnId;
          yield toRunResult(message);
          if (completed) {
            finished = true;
            break;
          }
          await deps.frame();
        }
        if (finished || abortSignal.aborted) return;
        await request;
      } finally {
        abortSignal.removeEventListener("abort", onAbort);
      }

      if (message.runState.type === "running") {
        message = applyAgentEvent(
          applyAgentEvent(message, { type: "error", content: "응답이 완료되기 전에 종료되었습니다." }, nextPartId(), deps.now()),
          { type: "done" },
          nextPartId(),
          deps.now(),
        );
      }
      yield toRunResult(message);
    },
  };
}
