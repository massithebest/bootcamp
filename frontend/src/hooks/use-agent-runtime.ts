/**
 * assistant-ui LocalRuntime + 세션 내 thread 목록.
 *
 * 메시지 저장·스트리밍 표시·취소·편집·재생성·분기와 thread 전환은 runtime이 맡는다.
 * 우리 코드는 Backend SSE를 `ChatModelAdapter`로 감싸고(`lib/chat-model-adapter.ts`), thread별
 * Backend conversation을 대응시킨다(`lib/agent-threads.ts`).
 */
import { useMemo } from "react";
import {
  useAuiState,
  useLocalRuntime,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";

import { conversationFor, createMemoryHistory, suggestionAdapter, threadListAdapter } from "@/lib/agent-threads";
import { createAgentChatAdapter } from "@/lib/chat-model-adapter";

/** thread 하나의 runtime. thread id는 목록 항목의 id다. */
function useAgentThreadRuntime() {
  const threadId = useAuiState((s) => s.threadListItem.id);
  const adapter = useMemo(() => createAgentChatAdapter(conversationFor(threadId)), [threadId]);
  const history = useMemo(() => createMemoryHistory(threadId), [threadId]);
  return useLocalRuntime(adapter, { adapters: { history, suggestion: suggestionAdapter } });
}

export function useAgentRuntime() {
  return useRemoteThreadListRuntime({
    runtimeHook: useAgentThreadRuntime,
    adapter: threadListAdapter,
  });
}
