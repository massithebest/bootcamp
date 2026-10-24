/**
 * 브라우저 세션 동안만 유지하는 thread 저장소.
 *
 * Backend에는 대화 목록·메시지 조회 API가 없으므로 thread 메타데이터(목록)와 메시지(history)를 메모리에 둔다.
 * Backend 대화 API가 생기면 이 파일의 `threadListAdapter`와 `createMemoryHistory`만
 * `RemoteThreadListAdapter`·`ThreadHistoryAdapter` 구현으로 교체한다.
 */
import type {
  RemoteThreadListAdapter,
  SuggestionAdapter,
  ThreadHistoryAdapter,
  ThreadMessage,
} from "@assistant-ui/react";
import { createAssistantStream } from "assistant-stream";

import { parseSuggestions } from "@/lib/suggestions";
import { createConversation, type AgentConversation } from "@/lib/chat-model-adapter";

type HistoryItem = Parameters<ThreadHistoryAdapter["append"]>[0];

const conversations = new Map<string, AgentConversation>();
const histories = new Map<string, HistoryItem[]>();

/** thread id 하나에 Backend conversation 하나. thread를 벗어났다 돌아와도 같은 대화를 잇는다. */
export function conversationFor(threadId: string): AgentConversation {
  let conversation = conversations.get(threadId);
  if (!conversation) {
    conversation = createConversation();
    conversations.set(threadId, conversation);
  }
  return conversation;
}

export function createMemoryHistory(threadId: string): ThreadHistoryAdapter {
  const upsert = async (item: HistoryItem) => {
    const items = histories.get(threadId) ?? [];
    const index = items.findIndex((existing) => existing.message.id === item.message.id);
    if (index === -1) items.push(item);
    else items[index] = item;
    histories.set(threadId, items);
  };
  return {
    async load() {
      const items = histories.get(threadId) ?? [];
      return {
        headId: items.at(-1)?.message.id ?? null,
        messages: items.map((item) => ({ message: item.message, parentId: item.parentId })),
      };
    },
    append: upsert,
    update: upsert,
    async delete(removed) {
      const ids = new Set(removed.map((item) => item.message.id));
      histories.set(threadId, (histories.get(threadId) ?? []).filter((item) => !ids.has(item.message.id)));
    },
  };
}

/**
 * 후속질문 adapter. 모델을 다시 호출하지 않고, 마지막 성공 assistant 메시지에 실린 검증된
 * `done.data.suggestions`만 돌려준다. Backend가 보내지 않으면 빈 배열이라 아무것도 표시되지 않는다.
 */
export const suggestionAdapter: SuggestionAdapter = {
  async generate({ messages }) {
    return branchSuggestions(messages.at(-1)).map((prompt) => ({ prompt }));
  },
};

/**
 * 현재 선택된 분기의 마지막 메시지에 실린 후속질문. adapter 결과는 실행이 끝날 때만 갱신되므로
 * 버전을 바꾸면 다른 분기의 질문이 남는다. 화면은 이 값을 분기마다 다시 읽는다.
 */
export function branchSuggestions(
  last: { role: string; status?: { type: string }; metadata?: { custom?: Record<string, unknown> } } | undefined,
): string[] {
  if (last?.role !== "assistant" || last.status?.type !== "complete") return [];
  return parseSuggestions(last.metadata?.custom?.suggestions) ?? [];
}

export const TITLE_MAX_LENGTH = 28;

/** 첫 사용자 질문을 그대로 줄여 제목으로 쓴다(모델 호출 없음). */
export function titleFromMessages(
  messages: readonly { role: string; content: readonly { type: string; text?: string }[] | string }[],
): string {
  const first = messages.find((message) => message.role === "user");
  const raw = !first
    ? ""
    : typeof first.content === "string"
      ? first.content
      : first.content.filter((part) => part.type === "text").map((part) => part.text ?? "").join("");
  const text = raw.replace(/\s+/g, " ").trim();
  return text.length > TITLE_MAX_LENGTH ? `${text.slice(0, TITLE_MAX_LENGTH - 1)}…` : text;
}

/**
 * 메모리 전용 thread 목록 adapter. 목록은 이번 브라우저 세션에서 만든 thread뿐이며
 * 새로고침하면 사라진다. 제목은 첫 질문을 줄여 만든다.
 */
export const threadListAdapter: RemoteThreadListAdapter = {
  async list() {
    return { threads: [] };
  },
  async initialize(threadId) {
    return { remoteId: threadId, externalId: undefined };
  },
  async rename() {},
  async archive() {},
  async unarchive() {},
  async delete(remoteId) {
    conversations.delete(remoteId);
    histories.delete(remoteId);
  },
  async fetch(threadId) {
    return { status: "regular", remoteId: threadId };
  },
  async generateTitle(_remoteId: string, messages: readonly ThreadMessage[]) {
    const title = titleFromMessages(messages);
    return createAssistantStream((controller) => {
      if (title) controller.appendText(title);
    });
  },
};

/** 테스트에서 상태를 비운다. */
export function resetAgentThreads(): void {
  conversations.clear();
  histories.clear();
}
