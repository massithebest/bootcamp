/** 개발 서버에서만 불러오는 회귀 harness. 앱 bundle에는 포함하지 않는다. */
import { act, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { useAgentChat, type UseAgentChatResult } from "@/hooks/use-agent-chat";
import type { AgentEvent, ChatMessage } from "@/types/chat";

function check(value: unknown, message: string): asserts value {
  if (!value) throw new Error(message);
}

export async function runChatRegressions() {
  const results: { name: string; error?: string }[] = [];
  const originalFetch = window.fetch;
  const encoder = new TextEncoder();
  const cases: Record<string, (h: Harness) => Promise<void>> = {
    "same tick duplicate send starts one request": async (h) => {
      await act(async () => {
        const thread = h.chat().runtime.thread;
        void thread.append({ role: "user", content: [{ type: "text", text: "하나" }] });
        void thread.append({ role: "user", content: [{ type: "text", text: "둘" }] });
      });
      check(h.requests.length === 1, "duplicate requests started");
      await h.finish(0, [{ type: "text", content: "답" }, { type: "done" }]);
    },
    "backend error remains an error message before first text": async (h) => {
      await h.send("질문");
      await h.finish(0, [{ type: "error", content: "업무 오류" }, { type: "done" }]);
      check(!h.chat().retryPrompt, "backend error confused with connection failure");
      check(h.chat().messages[1]?.runState.type === "error", "backend error hidden");
    },
    "retry reuses original user": async (h) => {
      await h.send("질문");
      await h.fail(0);
      check(h.chat().retryPrompt, "retry not offered");
      await act(async () => h.chat().handleRetry());
      await h.finish(1, [{ type: "text", content: "답변" }, { type: "done", data: { turn_id: "t1" } }]);
      check(h.chat().messages.filter(m => m.role === "user").length === 1, "duplicate user on retry");
    },
    "successful empty done is not a connection failure": async (h) => {
      await h.send("질문");
      await h.finish(0, [{ type: "done", data: { turn_id: "empty" } }]);
      check(!h.chat().retryPrompt, "success misclassified as connection failure");
      check(h.chat().messages.at(-1)?.turnId === "empty", "lost completed turn");
    },
    "cancel then new request ignores late stream": async (h) => {
      await h.send("첫 질문");
      await act(async () => h.chat().handleStop());
      await h.send("새 질문");
      await h.finish(0, [{ type: "text", content: "늦은 응답" }, { type: "done" }]);
      check(h.chat().streaming, "old request cleared new running state");
      await h.finish(1, [{ type: "text", content: "새 응답" }, { type: "done" }]);
      check(h.chat().messages[1].runState.type === "cancelled", "cancel status lost");
      check(!JSON.stringify(h.chat().messages).includes("늦은 응답"), "late output leaked");
    },
    "same tick cancel and append preserve cancelled message": async (h) => {
      await h.send("이전 질문");
      await act(async () => {
        h.chat().handleStop();
        void h.chat().runtime.thread.append({ role: "user", content: [{ type: "text", text: "즉시 새 질문" }] });
      });
      await h.finish(0, [{ type: "done" }]);
      await h.finish(1, [{ type: "text", content: "새 답" }, { type: "done" }]);
      check(h.chat().messages[1].runState.type === "cancelled", "stale prefix restored running message");
    },
    "regenerate and edit preserve fork anchor": async (h) => {
      await h.send("첫 질문");
      await h.finish(0, [{ type: "text", content: "첫 답" }, { type: "done", data: { turn_id: "t1" } }]);
      await h.send("둘째 질문");
      await h.finish(1, [{ type: "text", content: "둘째 답" }, { type: "done", data: { turn_id: "t2" } }]);
      await act(async () => { void h.chat().runtime.thread.getMessageByIndex(3).reload(); });
      check(h.requests[2].body.fork_from_turn_id === "t1", "reload anchor lost");
      await h.fail(2);
      await act(async () => h.chat().handleRetry());
      check(h.requests[3].body.fork_from_turn_id === "t1", "retry anchor lost");
      await h.finish(3, [{ type: "text", content: "재생성" }, { type: "done", data: { turn_id: "t3" } }]);
      await act(async () => h.chat().runtime.thread.getMessageByIndex(0).composer.beginEdit());
      await act(async () => h.chat().runtime.thread.getMessageByIndex(0).composer.setText("편집 질문"));
      await act(async () => h.chat().runtime.thread.getMessageByIndex(0).composer.send());
      check(h.requests[4].body.fork_from_turn_id === "", "first edit must restart");
      await h.finish(4, [{ type: "text", content: "편집 답" }, { type: "done" }]);
      check(h.chat().messages.length === 2, "edit did not replace suffix");
    },
    "reset rejects old response and resets conversation id": async (h) => {
      await h.send("이전");
      await act(async () => h.chat().resetConversation([]));
      await h.send("새 대화");
      await h.finish(0, [{ type: "error", content: "늦은 실패" }, { type: "done" }]);
      check(h.requests[0].body.conversation_id !== h.requests[1].body.conversation_id, "id not reset");
      check(h.chat().messages.length === 2 && !h.chat().retryPrompt, "reset contaminated");
      await h.finish(1, [{ type: "text", content: "답" }, { type: "done" }]);
    },
    "same tick reset and append use the new conversation": async (h) => {
      await h.send("이전 질문");
      await act(async () => {
        h.chat().resetConversation([]);
        void h.chat().runtime.thread.append({ role: "user", content: [{ type: "text", text: "새 대화" }] });
      });
      await h.finish(0, [{ type: "done" }]);
      await h.finish(1, [{ type: "text", content: "새 답" }, { type: "done" }]);
      check(h.chat().messages.length === 2, "stale prefix restored old conversation");
      check(h.requests[0].body.conversation_id !== h.requests[1].body.conversation_id, "conversation id reused");
    },
    "partial error preserves parts and assistant-ui incomplete status": async (h) => {
      await h.send("질문");
      await h.finish(0, [{ type: "text", content: "앞" }, { type: "tool_result", tool_name: "execute_sql", data: { status: "ok" } }, { type: "text", content: "뒤" }, { type: "error", content: "안전한 오류" }, { type: "done" }]);
      check(h.chat().messages[1].parts.map(p => p.kind).join() === "text,tool,text", "parts reordered");
      const status = h.chat().runtime.thread.getMessageByIndex(1).getState().status;
      check(status?.type === "incomplete" && status.reason === "error", "runtime error status lost");
    },
  };
  type Pending = { body: Record<string, unknown>; controller: ReadableStreamDefaultController<Uint8Array> };
  type Harness = { chat: () => UseAgentChatResult; requests: Pending[]; send: (text: string) => Promise<void>; fail: (index: number) => Promise<void>; finish: (index: number, events: AgentEvent[]) => Promise<void> };
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  try {
    for (const [name, run] of Object.entries(cases)) {
      const requests: Pending[] = [];
      window.fetch = async (_input, init) => new Response(new ReadableStream<Uint8Array>({
        start(controller) { requests.push({ body: JSON.parse(String(init?.body)), controller }); },
      }));
      let current: UseAgentChatResult;
      function Probe() { current = useAgentChat([] as ChatMessage[]); return null; }
      const host = document.createElement("div");
      document.body.append(host);
      const root = createRoot(host);
      const h: Harness = {
        chat: () => current,
        requests,
        send: async (text) => { await act(async () => { void current.runtime.thread.append({ role: "user", content: [{ type: "text", text }] }); }); },
        fail: async (index) => { await act(async () => requests[index].controller.error(new TypeError("network fixture"))); },
        finish: async (index, events) => {
          check(requests[index], `request ${index} missing`);
          await act(async () => {
            requests[index].controller.enqueue(encoder.encode(events.map(e => `data: ${JSON.stringify(e)}\n\n`).join("")));
            requests[index].controller.close();
          });
        },
      };
      try {
        await act(async () => root.render(<StrictMode><Probe /></StrictMode>));
        await run(h);
        results.push({ name });
      } catch (e) { results.push({ name, error: String(e) }); }
      finally { await act(async () => root.unmount()); host.remove(); }
    }
  } finally { window.fetch = originalFetch; Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: false }); }
  return results;
}
