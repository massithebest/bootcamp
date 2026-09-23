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
  const originalStubUser = window.localStorage.getItem("pp.knowledge.stub-user");
  window.localStorage.setItem("pp.knowledge.stub-user", "user");
  window.confirm = () => true;
  let stream: ReadableStreamDefaultController<Uint8Array> | undefined;
  const encoder = new TextEncoder();
  let failSave = false;
  // 구조화 지식 편집 시나리오용 고정 응답. 켜기 전에는 기존 회귀와 같은 빈 응답을 돌려준다.
  const editorFixture = { on: false, permissions: ["knowledge:write"], changeStatus: 500, userId: "user" };
  const entryRow = { type: "table", id: "wip", title: "wip", summary: "재공", status: "verified", source: "", owner: "", updated: "", active: true, archived: false, pending_change: null };
  const guide = { kind: "table", key_field: "table", immutable: ["table"], template: { table: "", description: "", active: true }, fields: [
    { name: "table", path: "table", label: "테이블명", help: "", required: true, readonly: false, widget: "string", group: "기본 정보" },
    { name: "description", path: "description", label: "설명", help: "", required: true, readonly: false, widget: "text", group: "기본 정보" },
  ] };
  const editorApi = (url: string, init?: RequestInit): Response | undefined => {
    if (!editorFixture.on) return undefined;
    const path = url.replace(/^.*\/api/, "");
    if (path === "/me") {
      const id = new Headers(init?.headers).get("X-User-Id") || editorFixture.userId;
      return Response.json({ id, name: id === "user" ? "사용자" : "검토자", permissions: editorFixture.permissions, mode: "stub", knowledge_management: true, allow_self_approval: false, stub_users: [{ id: "user", name: "사용자" }, { id: "reviewer", name: "검토자" }] });
    }
    if (path.startsWith("/knowledge/entries/table/wip")) return Response.json({ ...entryRow, detail: { table: "wip" } });
    if (path.startsWith("/knowledge/entries")) return Response.json([entryRow]);
    if (path === "/knowledge/guides/table") return Response.json(guide);
    if (path === "/knowledge/source/table/wip") return Response.json({ kind: "table", key: "wip", yaml: "table: wip\n", data: { table: "wip", description: "기존 설명", active: true } });
    if (path === "/knowledge/validate") return Response.json({ ok: true, parsed: true, yaml: "table: wip\n", data: {}, key: "wip", errors: [] });
    if (path === "/knowledge/changes" && init?.method === "POST") return new Response("secret backend detail", { status: editorFixture.changeStatus });
    if (path.startsWith("/knowledge/changes")) return Response.json([]);
    return undefined;
  };
  window.fetch = async (input, init) => {
    const url = String(input);
    const fixture = editorApi(url, init);
    if (fixture) return fixture;
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
    const found = Array.from(document.querySelectorAll<HTMLButtonElement>("button, [role=menuitem]")).find(b => b.textContent?.trim() === name || b.getAttribute("aria-label") === name);
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
  const selectValue = async (element: HTMLSelectElement, value: string) => {
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!.call(element, value);
      element.dispatchEvent(new Event("change", { bubbles: true }));
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
    await run("structured knowledge opens an editor and a conflicting save keeps the draft", async () => {
      Object.assign(editorFixture, { on: true, permissions: ["knowledge:write"], changeStatus: 409 });
      await act(async () => { window.dispatchEvent(new Event("knowledge-changed")); });
      await click("지식 관리");
      await waitFor(() => Array.from(host.querySelectorAll('section[aria-label="지식 목록"] li button')).some(b => b.textContent?.includes("wip")));
      await act(async () => Array.from(host.querySelectorAll<HTMLButtonElement>('section[aria-label="지식 목록"] li button')).find(b => b.textContent?.includes("wip"))!.click());
      await waitFor(() => Array.from(host.querySelectorAll("button")).some(b => b.textContent?.trim() === "수정 요청"));
      await click("수정 요청");
      await waitFor(() => !!host.querySelector("#field-description"));
      check((host.querySelector<HTMLInputElement>("#field-table"))!.readOnly, "existing identifier should be locked");
      const description = host.querySelector<HTMLTextAreaElement>("#field-description")!;
      check(description.value === "기존 설명", "current approved content was not loaded");
      await fill(description, "저장에 실패해도 남아야 하는 설명");
      await waitFor(() => host.textContent?.includes("검증을 통과했습니다") === true);
      await click("초안 저장");
      await waitFor(() => host.textContent?.includes("최신 내용을 다시 불러오세요") === true);
      check(host.querySelector<HTMLTextAreaElement>("#field-description")!.value === "저장에 실패해도 남아야 하는 설명", "failed save erased the draft");
      check(!host.textContent?.includes("secret backend detail"), "server text leaked into the UI");
      for (const [status, message] of [[403, "이 작업을 할 수 없습니다"], [422, "필수 입력과 글자 수를 확인하세요"]] as const) {
        editorFixture.changeStatus = status;
        await click("초안 저장");
        await waitFor(() => host.textContent?.includes(message) === true);
        check(host.querySelector<HTMLTextAreaElement>("#field-description")!.value === "저장에 실패해도 남아야 하는 설명", `${status} erased the draft`);
        check(!host.textContent?.includes("secret backend detail"), `${status} response leaked server text`);
      }
      await clickCurrentChat();
      check(document.querySelector('[role="dialog"]'), "unsaved editor changes were not guarded");
      const dialogButton = (text: string) => Array.from(document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button')).find(b => b.textContent === text)!;
      await act(async () => dialogButton("계속 편집").click());
      check(host.querySelector("#field-description"), "editor closed although the user chose to keep editing");
      await click("편집 닫기");
      await act(async () => dialogButton("변경 취소 후 이동").click());
      await frame();
      check(!host.querySelector("#field-description"), "editor stayed open after discarding");
    });
    await run("without write permission structured knowledge stays read-only", async () => {
      Object.assign(editorFixture, { on: true, permissions: [], changeStatus: 500 });
      await act(async () => { window.dispatchEvent(new Event("knowledge-changed")); });
      await waitFor(() => Array.from(host.querySelectorAll('section[aria-label="지식 목록"] li button')).some(b => b.textContent?.includes("wip")));
      await act(async () => Array.from(host.querySelectorAll<HTMLButtonElement>('section[aria-label="지식 목록"] li button')).find(b => b.textContent?.includes("wip"))!.click());
      await waitFor(() => host.textContent?.includes("작성 권한이 없어 볼 수만 있습니다") === true);
      check(!Array.from(host.querySelectorAll("button")).some(b => b.textContent?.trim() === "수정 요청"), "edit request offered without permission");
      check(!host.querySelector('[aria-label="구조화 지식 추가"]'), "new structured knowledge offered without permission");
      editorFixture.on = false;
      await act(async () => { window.dispatchEvent(new Event("knowledge-changed")); });
      await clickCurrentChat(); await frame();
    });
    await run("switching the stub user preserves an unsaved text draft", async () => {
      Object.assign(editorFixture, { on: true, permissions: ["knowledge:write"], userId: "user" });
      await act(async () => { window.dispatchEvent(new Event("knowledge-changed")); });
      await click("지식 관리"); await click("+ 새 지식 추가"); await click("텍스트 지식 등록");
      const title = host.querySelector<HTMLInputElement>('input[name="title"]')!;
      await fill(title, "사용자 전환 중 보존할 초안");
      await selectValue(host.querySelector<HTMLSelectElement>('[aria-label="작업 사용자"]')!, "reviewer");
      await waitFor(() => host.querySelector<HTMLSelectElement>('[aria-label="작업 사용자"]')?.value === "reviewer");
      check(title.value === "사용자 전환 중 보존할 초안", "user switch erased the text draft");
      await clickCurrentChat();
      const dialogButton = (text: string) => Array.from(document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button')).find(b => b.textContent === text)!;
      await act(async () => dialogButton("변경 취소 후 이동").click());
      await frame();
      editorFixture.on = false;
      await act(async () => { window.dispatchEvent(new Event("knowledge-changed")); });
    });
    await run("dirty navigation supports stay and discard", async () => {
      await click("지식 관리"); await click("+ 새 지식 추가"); await click("텍스트 지식 등록");
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
      await click("지식 관리"); await click("+ 새 지식 추가"); await click("텍스트 지식 등록");
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
    if (originalStubUser === null) window.localStorage.removeItem("pp.knowledge.stub-user");
    else window.localStorage.setItem("pp.knowledge.stub-user", originalStubUser);
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: false });
  }
  return results;
}
