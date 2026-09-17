/** Actual App + deterministic SSE. Never contacts a provider or mutates production data. */
import { act } from "react";
import { createRoot } from "react-dom/client";
import App from "@/App";
import type { AgentEvent } from "@/types/chat";
import "@/app/globals.css";

function check(value: unknown, message: string): asserts value { if (!value) throw new Error(message); }

export async function runWorkbenchRegressions() {
  const results: { name: string; error?: string }[] = [];
  const originalFetch = window.fetch;
  const originalConfirm = window.confirm;
  const requests: ReadableStreamDefaultController<Uint8Array>[] = [];
  const encoder = new TextEncoder();
  const resultId = "a".repeat(32);
  window.confirm = () => true;
  window.fetch = async input => {
    const url = String(input);
    if (url.endsWith("/api/chat")) return new Response(new ReadableStream({ start(c) { requests.push(c); } }));
    if (url.endsWith("/api/knowledge/tools")) return Response.json([{
      name: "execute_sql", description: "읽기 전용 SQL을 실행합니다.", output: "조회 결과", status: "available",
      input_schema: { type: "object", properties: { secret_schema_marker: { type: "string" } } },
    }]);
    if (url.endsWith("/api/knowledge/skills")) return Response.json([{
      name: "kpi-shortfall-analysis", description: "실적 부진 원인을 검증하는 업무 절차입니다.", status: "active",
    }]);
    if (url.endsWith("/api/knowledge/skills/kpi-shortfall-analysis")) return Response.json({
      name: "kpi-shortfall-analysis", description: "실적 부진 원인을 검증하는 업무 절차입니다.", status: "active",
      content: "# 실적 부진 원인 분석\n\n## 절차\n\n1. **KPI 확정**: `list_kpis`로 정의를 확인한다.\n2. **가설 검증**: 근거 수치로 검증한다.\n\n## 규칙\n\n- 기각 근거도 답변에 남긴다.",
    });
    if (url.includes("/api/visualizations/")) return Response.json({
      visualization_id: "b".repeat(32), result_id: resultId, schema_version: 1, expires_at: "2099-01-01T00:00:00Z", warnings: [],
      chart: { type: "bar", x: "part", series: [{ key: "qty", label: "WIP" }], categories: ["A"], data: [{ part: "A", qty: 20 }], title: "WIP 비교", x_label: "제품", y_label: "수량", unit: "개" },
    });
    return Response.json([]);
  };
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  const host = document.createElement("div");
  document.body.append(host);
  const root = createRoot(host);
  const visible = (el: HTMLElement) => !!el.getClientRects().length && getComputedStyle(el).visibility !== "hidden";
  const button = (name: string) => {
    const found = [...host.querySelectorAll<HTMLButtonElement>("button")].find(b => visible(b) && (b.textContent?.trim() === name || b.getAttribute("aria-label") === name));
    check(found, `button missing: ${name}; sidebar=${host.querySelector('aside')?.className}; focus=${document.activeElement?.getAttribute('aria-label')}`); return found;
  };
  const click = async (name: string) => { await act(async () => { button(name).click(); }); };
  const pause = async (ms = 260) => { await act(async () => { await new Promise(resolve => setTimeout(resolve, ms)); }); };
  const waitFor = async (predicate: () => boolean) => {
    const deadline = performance.now() + 4000;
    while (!predicate() && performance.now() < deadline) await pause(50);
    check(predicate(), "timed out waiting for UI");
  };
  const fill = async (input: HTMLInputElement | HTMLTextAreaElement, value: string) => {
    await act(async () => {
      Object.getOwnPropertyDescriptor(input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, "value")!.set!.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  };
  const composer = () => host.querySelector<HTMLTextAreaElement>('[aria-label="메시지 입력"]')!;
  const send = async () => { await fill(composer(), "UX 검증 질문"); await click("전송"); };
  const emit = async (...events: AgentEvent[]) => {
    await act(async () => {
      const stream = requests.at(-1)!;
      stream.enqueue(encoder.encode(events.map(e => `data: ${JSON.stringify(e)}\n\n`).join("")));
      if (events.at(-1)?.type === "done") stream.close();
    });
  };
  const openSidebar = async () => {
    if (host.querySelector('button[aria-label="사이드바 펼치기"]')) await click("사이드바 펼치기");
    await pause();
  };
  const newChat = async () => { await openSidebar(); await click("새 채팅"); if (innerWidth < 860) await click("사이드바 접기"); await pause(); };
  const group = () => [...host.querySelectorAll<HTMLButtonElement>('[data-slot="tool-group-trigger"]')].at(-1)!;
  const run = async (name: string, body: () => Promise<void>) => {
    try { await body(); results.push({ name }); } catch (error) { results.push({ name, error: String(error) }); }
    finally { window.confirm = () => true; }
  };
  try {
    await act(async () => root.render(<App />));
    await pause();
    await run(`F04/F14 panels preserve Chat width and Inspector filters at ${innerWidth}px`, async () => {
      const mainWidth = host.querySelector("main")!.clientWidth;
      if (!visible(host.querySelector<HTMLElement>('aside[aria-label="참고 정보 인스펙터"] > div')!)) await click("인스펙터 펼치기");
      await pause();
      if (innerWidth < 1180) check(host.querySelector("main")!.clientWidth === mainWidth, "overlay compressed Chat");
      const resizeHandle = host.querySelector<HTMLElement>('[data-slot="inspector-resize-handle"]')!;
      check(resizeHandle?.getAttribute("role") === "separator" && resizeHandle.tabIndex === 0, "inspector resize handle is not keyboard accessible");
      const initialInspectorWidth = Number(resizeHandle.getAttribute("aria-valuenow"));
      await act(async () => resizeHandle.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true })));
      check(Number(resizeHandle.getAttribute("aria-valuenow")) > initialInspectorWidth, "ArrowLeft did not expand Inspector");
      await act(async () => resizeHandle.dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true })));
      check(resizeHandle.getAttribute("aria-valuenow") === resizeHandle.getAttribute("aria-valuemin"), "Home did not set minimum Inspector width");
      await act(async () => resizeHandle.dispatchEvent(new MouseEvent("dblclick", { bubbles: true })));
      check(Number(resizeHandle.getAttribute("aria-valuenow")) >= initialInspectorWidth, "double click did not restore default Inspector width");
      const toolsPanel = host.querySelector<HTMLElement>("#inspector-panel-tools")!;
      await waitFor(() => !!toolsPanel.querySelector("summary"));
      await act(async () => toolsPanel.querySelector<HTMLElement>("summary")!.click());
      check(!toolsPanel.textContent?.includes("입력 명세") && !toolsPanel.textContent?.includes("secret_schema_marker"), "tool input schema remains visible");
      await click("스킬");
      const skillsPanel = host.querySelector<HTMLElement>("#inspector-panel-skills")!;
      await waitFor(() => [...skillsPanel.querySelectorAll("button")].some(item => item.textContent?.includes("kpi-shortfall-analysis")));
      check(getComputedStyle(skillsPanel).scrollbarGutter === "stable", "Inspector does not reserve scrollbar space");
      const skillTrigger = [...skillsPanel.querySelectorAll<HTMLButtonElement>("button")].find(item => item.textContent?.includes("kpi-shortfall-analysis"))!;
      const skillDescription = skillsPanel.querySelector<HTMLElement>("article header p")!;
      const descriptionWidth = skillDescription.getBoundingClientRect().width;
      check(skillTrigger.getAttribute("aria-expanded") === "false" && !skillsPanel.querySelector("ol"), "skill detail is not collapsed initially");
      await act(async () => skillTrigger.click());
      await waitFor(() => !!skillsPanel.querySelector("ol"));
      check(skillDescription.getBoundingClientRect().width === descriptionWidth, "Inspector scrollbar changed text width");
      check(skillTrigger.getAttribute("aria-expanded") === "true", "skill dropdown did not expand");
      check(skillsPanel.querySelector("h3")?.textContent === "kpi-shortfall-analysis", "skill name hierarchy missing");
      check(skillsPanel.querySelector("h4")?.textContent === "실적 부진 원인 분석", "skill markdown title is not rendered");
      check(!!skillsPanel.querySelector("ol strong") && !skillsPanel.textContent?.includes("## 절차"), "skill markdown remains raw");
      await click("지식");
      const search = host.querySelector<HTMLInputElement>('[aria-label="우측 지식 검색"]')!;
      await fill(search, "wip");
      await click("도구"); await click("지식");
      check(host.querySelector<HTMLInputElement>('[aria-label="우측 지식 검색"]')!.value === "wip", "tab reset query");
      await click("인스펙터 접기"); await pause();
      check(composer().clientWidth > 250, "composer too narrow after close");
      await click("인스펙터 펼치기"); await pause();
      check(search.value === "wip", "panel reset query");
      if (innerWidth < 1180) {
        await act(async () => { search.focus(); search.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
        await pause();
        check(document.activeElement?.getAttribute("aria-label") === "인스펙터 펼치기", "Escape did not return focus");
      } else await click("인스펙터 접기");
    });
    await run("F08 new chat and example session navigation do not request confirmation", async () => {
      await openSidebar(); await fill(composer(), "전환 전 초안");
      let confirmations = 0;
      window.confirm = () => { confirmations++; return false; };
      await click("새 채팅");
      check(confirmations === 0, "new chat requested confirmation");
      check(composer().value === "", "new chat did not clear draft");
      check(!host.querySelector('[data-slot="aui_message-group"]')?.textContent?.trim(), "new chat retained old messages");
      await fill(composer(), "세션 선택 전 초안");
      const other = [...host.querySelectorAll<HTMLButtonElement>('nav[aria-label="최근 대화"] button')].find(b => b.getAttribute("aria-current") !== "true")!;
      await act(async () => other.click());
      check(confirmations === 0, "session selection requested confirmation");
      check(other.getAttribute("aria-current") === "true", "session selection did not complete");
      check(composer().value === "", "session selection did not clear draft");
      window.confirm = () => true;
      if (innerWidth < 860) await click("사이드바 접기");
    });
    await run("F02/F07/F09/F10 tool error + missing result + done preserves focus and honest summary", async () => {
      await newChat(); await send();
      const live = host.querySelector('[data-slot="execution-announcement"]');
      await emit({ type: "tool_call", tool_name: "execute_sql", tool_call_id: "error", data: { args: {} } },
        { type: "tool_call", tool_name: "execute_sql", tool_call_id: "missing", data: { args: {} } });
      check(live === host.querySelector('[data-slot="execution-announcement"]'), "live region remounted");
      const tool = host.querySelector<HTMLButtonElement>('[data-slot="tool-call"] button')!;
      await act(async () => tool.focus());
      await emit({ type: "tool_result", tool_name: "execute_sql", tool_call_id: "error", data: { status: "error", message: "조건 확인" } },
        { type: "text", content: "일부 조회를 완료하지 못했습니다." }, { type: "done" });
      await pause();
      check(group().getAttribute("aria-expanded") === "false", "group did not auto-collapse");
      check(document.activeElement === group(), "auto-collapse lost focus");
      check(group().textContent?.includes("오류 1개") && group().textContent?.includes("미완료 1개"), "misleading success summary");
      check(!group().querySelector('[data-slot="tool-group-trigger-complete"]'), "success icon on errors");
      const timer = host.querySelector('[data-slot="observed-duration"]')!;
      check(timer.textContent?.includes("응답 시간"), "timing scope missing");
      const finished = timer.textContent; await pause(1100);
      check(timer.textContent === finished, "completed timer kept ticking");
      check(!live?.textContent?.includes("초"), "timer leaked into live announcement");
    });
    await run("F03/F08 actions remain keyboard reachable and cancelled regeneration preserves answer", async () => {
      const copies = [...host.querySelectorAll<HTMLButtonElement>('button[aria-label="복사"]')];
      check(copies.length >= 2, "earlier copy action is unmounted");
      await act(async () => copies[0].focus());
      check(document.activeElement === copies[0], "copy cannot receive keyboard focus");
      const before = requests.length;
      window.confirm = () => false;
      await click("재생성");
      check(requests.length === before && host.textContent?.includes("일부 조회를 완료하지 못했습니다."), "cancel regenerated answer");
      window.confirm = () => true;
    });
    await run("F12 empty done has explicit feedback", async () => {
      await newChat(); await send(); await emit({ type: "done" });
      check(host.querySelector('[data-slot="empty-response"]'), "empty assistant has no explanation");
    });
    await run("F12/F16 zero-row success and bounded SQL details", async () => {
      await newChat(); await send();
      await emit({ type: "tool_call", tool_name: "execute_sql", tool_call_id: "zero", data: { args: {} } },
        { type: "tool_result", tool_name: "execute_sql", tool_call_id: "zero", data: { status: "ok", row_count: 0, table: { columns: ["qty"], rows: [] }, sql: Array(150).fill("SELECT 1").join("\n") } }, { type: "done" });
      await act(async () => group().click());
      const groupContent = host.querySelector<HTMLElement>('[data-slot="tool-group-content"]')!;
      check(getComputedStyle(groupContent).animationName === "none", "completed ToolGroup still animates its layout");
      await act(async () => host.querySelector<HTMLButtonElement>('[data-slot="tool-call"] button')!.click());
      await waitFor(() => !!host.textContent?.includes("조회 결과 0건"));
      await click("실행된 SQL"); await pause();
      const sql = host.querySelector<HTMLElement>('[aria-label="실행된 SQL 전체 내용"]')!;
      check(sql.clientHeight <= 384 && sql.scrollHeight > sql.clientHeight, "SQL not internally scrollable");
      check(sql.textContent?.split("\n").length === 150, "SQL was truncated");
      check(host.textContent?.includes("소요"), "tool observation absent from detail");
    });
    await run("F01/F05/F06/F15 separate table, long tokens, headings and readable metadata", async () => {
      await newChat(); await send();
      const long = "LOT_".repeat(120);
      await emit({ type: "text", content: `# 분석\n\n### 세부\n\n${long}\n\n| 지표 | 비율 |\n| --- | --- |\n| 불량률 | 2% |` },
        { type: "tool_call", tool_name: "prepare_table", tool_call_id: "table", data: { args: { result_id: resultId } } },
        { type: "tool_result", tool_name: "prepare_table", tool_call_id: "table", data: { status: "ok", result_id: resultId, title: "WIP", columns: ["제품", "WIP"], rows: [["A", 20]], row_count: 1, displayed_count: 1, source_truncated: false } }, { type: "done" });
      await waitFor(() => !!host.textContent?.includes(long));
      check(host.textContent?.includes("불량률"), "separate Markdown table disappeared");
      const paragraph = [...host.querySelectorAll("p")].find(p => p.textContent === long)!;
      check(paragraph.scrollWidth <= paragraph.clientWidth + 1, "long token clipped");
      check(host.querySelectorAll("main").length === 1 && host.querySelector("h2"), "missing landmark/message heading");
      check(host.querySelector("h3")?.textContent === "분석" && host.querySelector("h4")?.textContent === "세부", `heading level skipped: ${[...host.querySelectorAll('h3,h4')].map(e => `${e.tagName}:${e.textContent}`).join(',')}`);
      const th = host.querySelector("th")!;
      check(getComputedStyle(th).color === "rgb(85, 96, 109)", "table header still low contrast");
    });
    await run("F13 chart data alternative uses real values", async () => {
      await newChat(); await send();
      await emit({ type: "tool_call", tool_name: "prepare_visualization", tool_call_id: "chart", data: { args: { result_id: resultId } } },
        { type: "tool_result", tool_name: "prepare_visualization", tool_call_id: "chart", data: { status: "ok", visualization_id: "b".repeat(32) } }, { type: "done" });
      await waitFor(() => !!host.textContent?.includes("차트 데이터 표로 보기"));
      await click("차트 데이터 표로 보기");
      await waitFor(() => !!host.querySelector("table"));
      check(host.querySelector("table")?.textContent?.includes("A20"), `chart alternative values differ: ${host.querySelector('table')?.textContent}`);
    });
    await run("F11/F17 reduced motion and unconnected controls are explicit", async () => {
      check(host.querySelector('[aria-label="모델 GLM-5.3-Flash, 설정 기능 미연결"]'), "model display does not disclose its unconnected control");
      check(host.querySelector('[aria-label="추론 강도 중간, 조절 기능 미연결"]'), "reasoning display does not disclose its unconnected control");
      check(host.textContent?.includes("GLM-5.3-Flash") && host.textContent?.includes("중간"), "requested model metadata is absent");
      await newChat(); await send();
      const spinner = host.querySelector('[data-slot="execution-pending-spinner"]')!;
      check(getComputedStyle(spinner).animationName === (matchMedia('(prefers-reduced-motion: reduce)').matches ? "none" : "spin"), "motion preference ignored");
      await click("중단");
      const elapsed = host.querySelector('[data-slot="observed-duration"]')?.textContent;
      await pause(1100);
      check(host.querySelector('[data-slot="observed-duration"]')?.textContent === elapsed, "cancel did not stop timer");
    });
  } finally {
    await act(async () => root.unmount()); host.remove(); window.fetch = originalFetch; window.confirm = originalConfirm;
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: false });
  }
  return results;
}
