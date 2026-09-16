/** Browser-only lifecycle regressions. No provider or production storage requests. */
import { act } from "react";
import { createRoot } from "react-dom/client";
import App from "@/App";
import "@/app/globals.css";

function check(value: unknown, message: string): asserts value { if (!value) throw new Error(message); }
export async function runKnowledgeWorkspaceRegressions() {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  const results: { name: string; error?: string }[] = [];
  const originalFetch = window.fetch;
  const originalConfirm = window.confirm;
  window.confirm = () => true;
  let stream: ReadableStreamDefaultController<Uint8Array> | undefined;
  const encoder = new TextEncoder();
  let failSave = false;
  window.fetch = async (input, init) => {
    const url = String(input);
    if (url.endsWith("/api/chat")) return new Response(new ReadableStream({ start(c) { stream = c; } }));
    if (url.includes("/documents") && init?.method === "POST") {
      if (failSave) return new Response("internal error", { status: 503 });
      throw new Error("Unexpected mutation in workspace fixture");
    }
    return Response.json([]);
  };
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const button = (name: string) => {
    const found = Array.from(host.querySelectorAll<HTMLButtonElement>("button")).find(b => b.textContent?.trim() === name || b.getAttribute("aria-label") === name);
    check(found, `button missing: ${name}`); return found;
  };
  const click = async (name: string) => { await act(async () => button(name).click()); };
  const clickCurrentChat = async () => {
    const current = host.querySelector<HTMLButtonElement>('nav[aria-label="최근 대화"] button[aria-current="true"]');
    check(current, "current chat missing from recent conversations");
    await act(async () => current.click());
  };
  const fill = async (element: HTMLInputElement | HTMLTextAreaElement, text: string) => {
    await act(async () => {
      Object.getOwnPropertyDescriptor(element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, "value")!.set!.call(element, text);
      element.dispatchEvent(new Event("input", { bubbles: true }));
    });
  };
  const frame = async () => { await act(async () => { await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))); }); };
  const waitFor = async (predicate: () => boolean) => {
    const end = performance.now() + 5000;
    while (!predicate() && performance.now() < end) await frame();
    check(predicate(), "Timed out waiting for rendered content");
  };
  const run = async (name: string, body: () => Promise<void>) => {
    try { await body(); results.push({ name }); } catch (e) { results.push({ name, error: String(e) }); }
  };
  try {
    await act(async () => root.render(<App />));
    await run("composer node and draft survive management round trip", async () => {
      const mainItems = Array.from(host.querySelectorAll('nav[aria-label="주요 메뉴"] button')).map(b => b.textContent?.trim());
      check(JSON.stringify(mainItems) === JSON.stringify(["새 채팅", "지식 관리"]), "unexpected primary navigation");
      const input = host.querySelector<HTMLTextAreaElement>('[aria-label="메시지 입력"]')!;
      await fill(input, "작성 중 문장");
      await click("지식 관리");
      check(button("지식 관리").getAttribute("aria-current") === "page", "knowledge navigation is not current");
      check(!host.textContent?.includes("대화로 돌아가기"), "legacy return button remains");
      await clickCurrentChat(); await frame();
      check(host.querySelector('[aria-label="메시지 입력"]') === input, "composer remounted");
      check(input.value === "작성 중 문장", "composer draft lost");
    });
    await run("new chat stays reachable from recent conversations", async () => {
      await click("새 채팅");
      const current = host.querySelector<HTMLButtonElement>('nav[aria-label="최근 대화"] button[aria-current="true"]');
      check(current?.textContent?.includes("새 대화"), "new chat missing from recent conversations");
      const input = host.querySelector<HTMLTextAreaElement>('[aria-label="메시지 입력"]')!;
      await fill(input, "새 채팅 초안");
      await click("지식 관리"); await clickCurrentChat(); await frame();
      check(host.querySelector('[aria-label="메시지 입력"]') === input, "new chat composer remounted");
      check(input.value === "새 채팅 초안", "new chat draft lost");
    });
    await run("stream completes while management is open and scroll restores", async () => {
      await click("전송"); check(stream, "SSE did not start");
      const text = "스트리밍 응답\n\n".repeat(40);
      await act(async () => stream!.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text", content: text })}\n\n`)));
      const viewport = host.querySelector<HTMLElement>('[data-slot="aui_thread-viewport"]')!;
      await waitFor(() => viewport.scrollHeight > viewport.clientHeight + 100); viewport.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true })); viewport.scrollTop = 70;
      viewport.dispatchEvent(new Event("scroll", { bubbles: true }));
      const saved = viewport.scrollTop;
      await click("지식 관리");
      await act(async () => {
        stream!.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text", content: "관리 중 수신한 마지막 응답" })}\n\ndata: ${JSON.stringify({ type: "done", data: { turn_id: "knowledge-test" } })}\n\n`));
        stream!.close();
      });
      await clickCurrentChat(); await frame();
      await waitFor(() => host.textContent?.includes("관리 중 수신한 마지막 응답") === true);
      check(Math.abs(viewport.scrollTop - saved) < 2, `scroll changed: ${saved} -> ${viewport.scrollTop}`);
    });
    await run("dirty navigation supports stay and discard", async () => {
      await click("지식 관리"); await click("텍스트 지식 등록");
      await fill(host.querySelector<HTMLInputElement>('input[name="title"]')!, "미저장 제목");
      await clickCurrentChat();
      check(document.querySelector('[role="dialog"]'), "dirty dialog absent");
      const dialogButton = (text: string) => Array.from(document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button')).find(b => b.textContent === text)!;
      await act(async () => dialogButton("계속 편집").click());
      check(host.querySelector<HTMLInputElement>('input[name="title"]')!.value === "미저장 제목", "stay discarded draft");
      await clickCurrentChat();
      await act(async () => dialogButton("변경 취소 후 이동").click());
      await frame();
      check(host.querySelector<HTMLElement>('[aria-label="메시지 입력"]')!.getClientRects().length > 0, "did not return to chat");
    });
    await run("failed save preserves fields and management remains available", async () => {
      await click("지식 관리"); await click("텍스트 지식 등록");
      for (const [name, value] of Object.entries({ title: "저장 실패 본문", content: "보존할 내용", owner: "담당자", source: "회의" })) {
        await fill(host.querySelector<HTMLInputElement | HTMLTextAreaElement>(`[name="${name}"]`)!, value);
      }
      failSave = true; await click("초안 저장");
      check(host.querySelector<HTMLInputElement>('[name="title"]')!.value === "저장 실패 본문", "failed save erased form");
      check(host.textContent?.includes("처리하지 못했습니다"), "save error missing");
      check(!button("텍스트 지식 등록").disabled, "management was disabled without a setting");
    });
  } finally {
    await act(async () => root.unmount()); host.remove(); window.fetch = originalFetch; window.confirm = originalConfirm;
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: false });
  }
  return results;
}
