/** 개발 서버에서만 불러오는 회귀 harness. 앱 bundle에는 포함하지 않는다. */
import { act, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AssistantRuntimeProvider, ThreadPrimitive, type AssistantRuntime } from "@assistant-ui/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AssistantMessage } from "@/components/chat/thread-messages";
import { useAgentRuntime } from "@/hooks/use-agent-runtime";
import { resetAgentThreads } from "@/lib/agent-threads";
import type { AgentEvent } from "@/types/chat";
import "@/app/globals.css";

function check(value: unknown, message: string): asserts value {
  if (!value) throw new Error(message);
}

export async function runChatRegressions() {
  const results: { name: string; error?: string }[] = [];
  const originalFetch = window.fetch;
  const encoder = new TextEncoder();
  const thread = (h: Harness) => h.runtime().thread;
  const messages = (h: Harness) => thread(h).getState().messages;
  const lastStatus = (h: Harness) => messages(h).at(-1)?.status;
  const cases: Record<string, (h: Harness) => Promise<void>> = {
    "backend error remains an error message before first text": async (h) => {
      await h.send("질문");
      await h.finish(0, [{ type: "error", content: "업무 오류" }, { type: "done" }]);
      const status = lastStatus(h);
      check(status?.type === "incomplete" && status.reason === "error", "backend error hidden");
      check(!thread(h).getState().isRunning, "run still marked running after error");
    },
    "transport failure is an error message and reload reuses the original user": async (h) => {
      await h.send("질문");
      await h.fail(0);
      const status = lastStatus(h);
      check(status?.type === "incomplete" && status.reason === "error", "connection failure not shown as error");
      await act(async () => { void thread(h).getMessageByIndex(1).reload(); });
      check(h.requests[1]?.body.message === "질문", "reload did not reuse the user text");
      await h.finish(1, [{ type: "text", content: "답변" }, { type: "done", data: { turn_id: "t1" } }]);
      check(messages(h).filter(m => m.role === "user").length === 1, "duplicate user on reload");
    },
    "successful empty done keeps the completed turn": async (h) => {
      await h.send("질문");
      await h.finish(0, [{ type: "done", data: { turn_id: "empty" } }]);
      const last = messages(h).at(-1);
      check(last?.status?.type === "complete", "success misclassified");
      check((last?.metadata.custom as { turnId?: string }).turnId === "empty", "lost completed turn");
    },
    "cancel then new request ignores late stream": async (h) => {
      await h.send("첫 질문");
      await act(async () => thread(h).cancelRun());
      await h.send("새 질문");
      await h.finish(0, [{ type: "text", content: "늦은 응답" }, { type: "done" }]);
      check(thread(h).getState().isRunning, "old request cleared new running state");
      await h.finish(1, [{ type: "text", content: "새 응답" }, { type: "done" }]);
      const first = messages(h)[1].status;
      check(first?.type === "incomplete" && first.reason === "cancelled", "cancel status lost");
      check(!JSON.stringify(messages(h)).includes("늦은 응답"), "late output leaked");
    },
    "regenerate and edit preserve fork anchor and keep branches": async (h) => {
      await h.send("첫 질문");
      await h.finish(0, [{ type: "text", content: "첫 답" }, { type: "done", data: { turn_id: "t1" } }]);
      await h.idle();
      await h.send("둘째 질문");
      await h.finish(1, [{ type: "text", content: "둘째 답" }, { type: "done", data: { turn_id: "t2" } }]);
      await h.idle();
      await act(async () => { void thread(h).getMessageByIndex(3).reload(); });
      check(h.requests[2].body.fork_from_turn_id === "t1", "reload anchor lost");
      await h.fail(2);
      await act(async () => { void thread(h).getMessageByIndex(3).reload(); });
      check(h.requests[3].body.fork_from_turn_id === "t1", "retry anchor lost");
      await h.finish(3, [{ type: "text", content: "재생성" }, { type: "done", data: { turn_id: "t3" } }]);
      await h.idle();
      check(thread(h).getMessageByIndex(3).getState().branchCount === 3, "regenerations were not kept as branches");
      await act(async () => thread(h).getMessageByIndex(0).composer.beginEdit());
      await act(async () => thread(h).getMessageByIndex(0).composer.setText("편집 질문"));
      await act(async () => thread(h).getMessageByIndex(0).composer.send());
      check(h.requests[4]?.body.fork_from_turn_id === "", "first edit must restart " + JSON.stringify(h.requests.map(r => r.body.fork_from_turn_id)));
      await h.finish(4, [{ type: "text", content: "편집 답" }, { type: "done" }]);
      await h.idle();
      check(messages(h).length === 2, "edit did not start a new branch path");
      check(thread(h).getMessageByIndex(0).getState().branchCount === 2, "edit did not keep the previous question");
    },
    "continuing an older branch forks from that branch turn": async (h) => {
      await h.send("첫 질문");
      await h.finish(0, [{ type: "text", content: "첫 답" }, { type: "done", data: { turn_id: "t1" } }]);
      await h.idle();
      await act(async () => { void thread(h).getMessageByIndex(1).reload(); });
      await h.finish(1, [{ type: "text", content: "다른 답" }, { type: "done", data: { turn_id: "t2" } }]);
      await h.idle();
      await act(async () => thread(h).getMessageByIndex(1).switchToBranch({ position: "previous" }));
      await h.send("이어서");
      check(h.requests[2].body.fork_from_turn_id === "t1", "older branch continuation did not fork");
    },
    "new thread gets a new conversation and rejects late output from the old one": async (h) => {
      await h.send("이전");
      await act(async () => {
        void h.runtime().threads.switchToNewThread();
        await new Promise<void>((resolve) => window.setTimeout(resolve, 50));
      });
      await h.send("새 대화");
      await h.finish(0, [{ type: "error", content: "늦은 실패" }, { type: "done" }]);
      check(h.requests[0].body.conversation_id !== h.requests[1].body.conversation_id, "conversation id reused");
      check(messages(h).length === 2 && lastStatus(h)?.type === "running", "old thread contaminated the new one");
      await h.finish(1, [{ type: "text", content: "답" }, { type: "done" }]);
    },
    "partial error preserves parts and assistant-ui incomplete status": async (h) => {
      await h.send("질문");
      await h.finish(0, [{ type: "text", content: "앞" }, { type: "tool_result", tool_name: "execute_sql", data: { status: "ok" } }, { type: "text", content: "뒤" }, { type: "error", content: "안전한 오류" }, { type: "done" }]);
      const content = messages(h)[1].content;
      check(content.map(p => p.type).join() === "tool-call,text", "parts reordered");
      const status = lastStatus(h);
      check(status?.type === "incomplete" && status.reason === "error", "runtime error status lost");
    },
  };
  type Pending = { body: Record<string, unknown>; controller: ReadableStreamDefaultController<Uint8Array> };
  type Harness = { runtime: () => AssistantRuntime; idle: () => Promise<void>; requests: Pending[]; send: (text: string) => Promise<void>; fail: (index: number) => Promise<void>; finish: (index: number, events: AgentEvent[]) => Promise<void> };
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  try {
    for (const [name, run] of Object.entries(cases)) {
      const requests: Pending[] = [];
      window.fetch = async (_input, init) => new Response(new ReadableStream<Uint8Array>({
        start(controller) { requests.push({ body: JSON.parse(String(init?.body)), controller }); },
      }));
      let current!: AssistantRuntime;
      function Probe() { current = useAgentRuntime(); return <AssistantRuntimeProvider runtime={current}>{null}</AssistantRuntimeProvider>; }
      resetAgentThreads();
      const host = document.createElement("div");
      document.body.append(host);
      const root = createRoot(host);
      const h: Harness = {
        runtime: () => current,
        // 스트림이 끝난 뒤 adapter의 마무리(head 갱신·최종 상태)까지 끝나기를 기다린다.
        idle: async () => {
          const deadline = performance.now() + 3_000;
          while (current.thread.getState().isRunning && performance.now() < deadline) {
            await act(async () => { await new Promise<void>((resolve) => window.setTimeout(resolve, 20)); });
          }
        },
        requests,
        send: async (text) => { await act(async () => { void current.thread.append({ role: "user", content: [{ type: "text", text }] }); }); },
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
        await Promise.race([
          run(h),
          new Promise<never>((_, reject) => window.setTimeout(() => reject(new Error("case timed out")), 8_000)),
        ]);
        results.push({ name });
      } catch (e) { results.push({ name, error: String(e) }); }
      finally { await act(async () => root.unmount()); host.remove(); }
    }
  } finally { window.fetch = originalFetch; Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: false }); }
  return results;
}

/** 실제 AssistantMessage DOM으로 실행 과정의 두 단계 disclosure를 검증한다. */
export async function runExecutionUiRegressions() {
  const name = "execution indicator distinguishes tool, writing, and completed phases";
  const originalFetch = window.fetch;
  const encoder = new TextEncoder();
  type Pending = {
    body: Record<string, unknown>;
    controller: ReadableStreamDefaultController<Uint8Array>;
  };
  const requests: Pending[] = [];
  let current!: AssistantRuntime;
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);

  window.fetch = async (_input, init) => new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      requests.push({ body: JSON.parse(String(init?.body)), controller });
    },
  }));

  function UIProbe() {
    current = useAgentRuntime();
    return (
      <AssistantRuntimeProvider runtime={current}>
        <TooltipProvider>
          <ThreadPrimitive.Root>
            <ThreadPrimitive.Viewport>
              <ThreadPrimitive.Messages>
                {({ message }) => message.role === "assistant" ? <AssistantMessage /> : null}
              </ThreadPrimitive.Messages>
            </ThreadPrimitive.Viewport>
          </ThreadPrimitive.Root>
        </TooltipProvider>
      </AssistantRuntimeProvider>
    );
  }

  // adapter가 스트림 갱신을 짧은 간격(16ms)으로 묶으므로 화면에 반영될 시간을 준다.
  const settle = () => new Promise<void>((resolve) => window.setTimeout(resolve, 60));
  const emit = async (events: AgentEvent[]) => {
    check(requests[0], "request missing");
    await act(async () => {
      requests[0].controller.enqueue(encoder.encode(
        events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""),
      ));
      await settle();
    });
  };

  const groupTrigger = () => host.querySelector<HTMLButtonElement>(
    '[data-slot="tool-group-trigger"]',
  );

  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  resetAgentThreads();
  try {
    await act(async () => root.render(<StrictMode><UIProbe /></StrictMode>));
    await act(async () => {
      void current.thread.append({
        role: "user",
        content: [{ type: "text", text: "WIP를 조회해줘" }],
      });
    });
    check(host.textContent?.includes("요청 분석 중"), "initial progress is delayed");
    const pending = host.querySelector<HTMLElement>('[data-slot="execution-pending"]');
    check(pending?.classList.contains("text-ui"), "initial progress text is still too small");
    check(pending?.classList.contains("text-ink-2"), "initial progress text is still too light");
    check(
      pending?.querySelector('[data-slot="execution-pending-spinner"]')?.classList.contains("top-px"),
      "initial progress icon is not optically aligned with its label",
    );

    await emit([{ type: "status", data: {
      step: "plan",
      label: "질의 분석",
      detail: "조회 범위 확인",
      status: "running",
    } }]);
    check(groupTrigger()?.textContent?.includes("실행 과정 진행 중"), "public status group missing");
    check(host.textContent?.includes("질의 분석"), "independent public status missing");

    await emit([
      { type: "text", content: "조회 범위를 확인한 뒤 WIP 데이터를 조회합니다." },
      { type: "tool_call", tool_name: "execute_sql", tool_call_id: "sql-1", data: {
        step: "sql-1",
        label: "데이터 조회",
        status: "running",
        args: { sql: "SELECT 1" },
      } },
    ]);
    check(groupTrigger()?.textContent?.includes("툴 1개 실행 중"), "tool group did not use running part status");
    check(groupTrigger()?.getAttribute("aria-expanded") === "true", "running group is not open");
    check(host.textContent?.includes("질의 분석"), "public status left the execution group");
    const progressText = host.querySelector<HTMLElement>('[data-slot="execution-progress-text"]');
    const toolRow = host.querySelector<HTMLElement>('[data-slot="tool-call"]');
    check(progressText?.textContent?.includes("WIP 데이터를 조회합니다"), "public pre-tool text disappeared during execution");
    check(progressText?.nextElementSibling === toolRow, "public pre-tool text is not directly above the running tool");
    check(!progressText?.textContent?.includes("진행 안내"), "obsolete progress heading remained");
    check(!progressText?.classList.contains("bg-accent-weak"), "progress text still uses the blue top block");
    const activeSpinner = groupTrigger()?.querySelector<SVGElement>('[data-slot="tool-group-trigger-loader"]');
    check(activeSpinner?.classList.contains("execution-activity-spinner"), "continuous activity spinner class is missing");
    check(activeSpinner?.classList.contains("animate-spin"), "activity spinner is not rotating");
    check(activeSpinner?.classList.contains("top-px"), "activity spinner is not optically aligned with its label");
    check(window.getComputedStyle(activeSpinner!).animationName !== "none", "activity spinner animation is not applied");

    await emit([
      { type: "tool_result", tool_name: "execute_sql", tool_call_id: "sql-1", data: { status: "ok", rows: [[1]] } },
      { type: "status", tool_name: "execute_sql", tool_call_id: "sql-1", data: { step: "sql-1", status: "completed" } },
    ]);
    check(current.thread.getState().isRunning, "fixture unexpectedly stopped before final text");
    check(groupTrigger()?.textContent?.includes("응답 작성 중 · 툴 1개 사용"), "writing phase is not distinguished after tools complete");
    check(groupTrigger()?.querySelector('[data-slot="tool-group-trigger-loader"]'), "activity spinner disappeared while writing");
    check(!host.querySelector('[data-slot="execution-progress-text"]'), "tool guidance remained after the tool completed");
    check(groupTrigger()?.getAttribute("aria-expanded") === "true", "group closed before the response completed");

    await emit([{ type: "text", content: "조회 결과입니다." }]);
    await act(async () => {
      // MarkdownTextPrimitive의 smooth 출력 속도는 환경별로 다르므로
      // 고정 지연 대신 본문이 완성될 때까지 짧게 polling한다.
      const deadline = performance.now() + 2_000;
      while (!host.textContent?.includes("조회 결과입니다.") && performance.now() < deadline) {
        await new Promise<void>((resolve) => window.setTimeout(resolve, 50));
      }
    });
    check(!host.querySelector('[data-slot="execution-progress-text"]'), "stale progress text remained after the next public output");
    check(host.textContent?.includes("조회 결과입니다."), "final response did not replace progress text");

    await act(async () => {
      requests[0].controller.enqueue(encoder.encode(
        `data: ${JSON.stringify({ type: "done" })}\n\n`,
      ));
      requests[0].controller.close();
      await settle();
    });
    check(groupTrigger()?.getAttribute("aria-expanded") === "false", "completed group did not collapse");
    check(groupTrigger()?.textContent?.includes("응답 작성 완료 · 툴 1개 사용"), "completed phase is not labelled");
    check(groupTrigger()?.querySelector('[data-slot="tool-group-trigger-complete"]'), "completed icon is missing");
    check(!groupTrigger()?.querySelector('[data-slot="tool-group-trigger-loader"]'), "spinner remained after completion");

    await act(async () => groupTrigger()?.click());
    const toolTrigger = host.querySelector<HTMLButtonElement>('[data-slot="tool-call"] button');
    check(toolTrigger, "tool row missing after reopening the group");
    await act(async () => toolTrigger.click());
    check(host.textContent?.includes("Parameters"), "tool parameters missing at the second disclosure level");
    check(host.textContent?.includes("Result"), "tool result missing at the second disclosure level");

    return [{ name }];
  } catch (error) {
    return [{ name, error: String(error) }];
  } finally {
    await act(async () => root.unmount());
    host.remove();
    window.fetch = originalFetch;
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: false });
  }
}
