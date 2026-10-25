import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { after, before, test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { z } from 'zod';

const contract = JSON.parse(readFileSync(new URL('./fixtures/present-vocabulary.json', import.meta.url), 'utf8')).tools;
const ID = 'a'.repeat(32);
const originalFetch = globalThis.fetch;
let server, PresentSqlPreviewToolUI, PresentChartToolUI, PresentTableToolUI, PresentSimulationToolUI, vocab, api, convertMessage, standalone, DatabaseResult, SimulationResult, ChartBlock, chartSummary, formatYAxisTick;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  ({ PresentSqlPreviewToolUI, PresentChartToolUI, PresentTableToolUI, PresentSimulationToolUI } =
    await server.ssrLoadModule('/src/components/chat/generative/present-tool-uis.tsx'));
  vocab = await server.ssrLoadModule('/src/components/chat/generative/vocabulary.ts');
  api = await server.ssrLoadModule('/src/lib/query-result-api.ts');
  ({ convertMessage } = await server.ssrLoadModule('/src/lib/chat-runtime.ts'));
  standalone = await server.ssrLoadModule('/src/lib/standalone-tools.ts');
  ({ DatabaseResult } = await server.ssrLoadModule('/src/components/chat/tool-results/database-result.tsx'));
  ({ SimulationResult } = await server.ssrLoadModule('/src/components/chat/tool-results/simulation-result.tsx'));
  ({ ChartBlock } = await server.ssrLoadModule('/src/components/chat/tool-results/chart-block.tsx'));
  ({ chartSummary } = await server.ssrLoadModule('/src/lib/chart-summary.ts'));
  ({ formatYAxisTick } = await server.ssrLoadModule('/src/components/chat/tool-results/charts/axis-format.ts'));
});
after(async () => { globalThis.fetch = originalFetch; await server.close(); });

/* ---------------- 계약: Backend present_* Tool과 같은 이름·prop·enum ---------------- */

const zodByTool = () => ({
  present_sql_preview: vocab.sqlPreviewArgs,
  present_chart: vocab.chartArgs,
  present_table: vocab.tableArgs,
  present_simulation: vocab.simulationArgs,
});

test('present tool set exposes exactly the Backend present_* Tool names', () => {
  assert.deepEqual(Object.keys(zodByTool()).sort(), Object.keys(contract).sort());
});

test('present tool arg schemas match the Backend contract exactly', () => {
  const zod = zodByTool();
  for (const [name, spec] of Object.entries(contract)) {
    const schema = z.toJSONSchema(zod[name]);
    const frontend = schema.properties ?? {};
    const backend = Object.keys(spec.props);
    assert.deepEqual(Object.keys(frontend).sort(), backend.sort(), name);
    for (const prop of backend) {
      for (const [constraint, expected] of Object.entries(spec.props[prop])) {
        assert.deepEqual(frontend[prop][constraint], expected, `${name}.${prop} ${constraint}`);
      }
    }
    assert.deepEqual([...(schema.required ?? [])].sort(), [...spec.required].sort(), `${name} required`);
  }
});

test('shared prop names have one type across present_* Tools (flat scalar args)', () => {
  const seen = new Map();
  for (const [name, spec] of Object.entries(contract)) {
    for (const [prop, def] of Object.entries(spec.props)) {
      if (!def.type) continue;
      assert.equal(seen.get(prop) ?? def.type, def.type, `${name}.${prop}`);
      seen.set(prop, def.type);
    }
  }
});

/* ---------------- present_* 렌더링 ---------------- */

const surface = (Component, args, status = { type: 'complete' }, extra = {}) => renderToStaticMarkup(createElement(Component, { args, status, result: { id: 'r', toolCallId: 'c', toolName: 'present_table', data: {} }, isError: false, ...extra }));

test('malformed present tool args render an inline notice and never throw', () => {
  const originalWarn = console.warn; console.warn = () => {};
  try {
    assert.match(surface(PresentChartToolUI, {}), /표시 설정이 올바르지 않아/);
    assert.doesNotMatch(surface(PresentChartToolUI, {}), /<script|onclick/i);
    assert.match(surface(PresentTableToolUI, { result_id: 'not-an-id' }), /표시 설정이 올바르지 않아/);
  } finally { console.warn = originalWarn; }
});

test('present_chart/present_table show stable loading states before data arrives and reject bad props', () => {
  assert.match(surface(PresentChartToolUI, { result_id: ID, chart_type: 'line', x_column: 'm', y_column: 'q' }), /차트를 불러오는 중/);
  assert.match(surface(PresentChartToolUI, { result_id: ID, chart_type: 'bar', bar_mode: 'stacked', x_column: 'm', y_column: 'q', group_by_column: 'line' }), /차트를 불러오는 중/);
  assert.match(surface(PresentChartToolUI, { result_id: ID, chart_type: 'bar', bar_mode: 'percent', x_column: 'm', y_column: 'q' }), /표시 설정이 올바르지 않아/);
  assert.match(surface(PresentTableToolUI, { result_id: ID }), /표를 불러오는 중/);
  assert.match(surface(PresentTableToolUI, { result_id: 'not-an-id' }), /표시 설정이 올바르지 않아/);
  assert.match(surface(PresentChartToolUI, { result_id: ID, chart_type: 'pie', x_column: 'm', y_column: 'q' }), /표시 설정이 올바르지 않아/);
  assert.match(surface(PresentSimulationToolUI, { scenario: 'HVLM', summary: '요약', kpis: [{ label: 'Part', value: 0, unit: '개' }] }), />0</);
});

test('present_sql_preview is collapsed by default and never emits SQL as markup', () => {
  const html = surface(PresentSqlPreviewToolUI, { sql: 'SELECT "<b>x</b>" FROM t' });
  assert.match(html, /실행 SQL/);
  assert.match(html, /aria-expanded="false"/);
  assert.doesNotMatch(html, /<b>x/);
});

test('present states: running, cancelled, failed and tool error are explicit', () => {
  assert.match(surface(PresentTableToolUI, {}, { type: 'running' }, { result: undefined }), /결과 화면을 구성하는 중/);
  assert.match(surface(PresentTableToolUI, {}, { type: 'incomplete', reason: 'cancelled' }, { result: undefined }), /중단/);
  assert.match(surface(PresentTableToolUI, {}, { type: 'incomplete', reason: 'error' }, { result: undefined }), /role="alert"[^>]*>결과 화면을 구성하지 못했습니다/);
  const failed = surface(PresentTableToolUI, { result_id: ID }, { type: 'complete' }, { result: { data: { status: 'error', message: '컬럼을 찾을 수 없습니다.' } }, isError: true });
  assert.match(failed, /컬럼을 찾을 수 없습니다/);
});

/* ---------------- API parser / URL / 요청 공유 ---------------- */

const table = (over = {}) => ({ status: 'ok', result_id: ID, page: 1, page_size: 50, row_count: 2, filtered_row_count: 2, source_truncated: false, columns: [{ name: 'a', dtype: 'int64', role: 'measure' }, { name: 'b', dtype: 'str', role: 'category' }], rows: [[1, 'x'], [2, null]], ...over });
const chart = (over = {}) => ({ status: 'ok', result_id: ID, chart: { type: 'area', x: 'm', series: [{ key: 'series_0', label: 'q' }], categories: ['2026-01'], data: [{ m: '2026-01', series_0: 1 }], title: null, x_label: 'm', y_label: 'q', unit: null }, warnings: [{ code: 'SOURCE_TRUNCATED', message: '잘림' }], ...over });

test('table parser accepts bounded pages and rejects malformed shapes', () => {
  assert.equal(api.parseQueryTablePage(table()).rows.length, 2);
  for (const bad of [
    table({ page: 0 }), table({ page_size: 101 }), table({ filtered_row_count: undefined }), table({ filtered_row_count: -1 }), table({ filtered_row_count: 3 }), table({ rows: [[1]] }), table({ rows: [[1, 'x', 3]] }), table({ rows: [[1, { a: 1 }]] }),
    table({ result_id: 'x' }), table({ status: 'error' }), table({ rows: Array.from({ length: 51 }, () => [1, 'x']) }), table({ columns: [{ name: 'a' }] }), null, [],
  ]) assert.equal(api.parseQueryTablePage(bad), null);
});

test('chart parser accepts area and enforces series/point bounds', () => {
  assert.equal(api.parseQueryChartResponse(chart()).chart.type, 'area');
  const c = chart().chart;
  for (const bad of [
    chart({ chart: { ...c, type: 'pie' } }), chart({ chart: { ...c, series: [] } }),
    chart({ chart: { ...c, series: Array.from({ length: 9 }, (_, i) => ({ key: `s${i}`, label: 'x' })) } }),
    chart({ chart: { ...c, categories: Array.from({ length: 501 }, (_, i) => i), data: [] } }),
    chart({ chart: { ...c, data: [{ m: '2026-01', series_0: 'NaN' }] } }),
    chart({ warnings: [{ code: 1 }] }), chart({ result_id: 'x' }),
  ]) assert.equal(api.parseQueryChartResponse(bad), null);
});

test('URLs use snake_case API names and include server table state', () => {
  const url = new URL(api.buildTableUrl({ resultId: ID, page: 2, pageSize: 25, columns: ['a', 'b'], search: 'part_3', sortColumn: 'a', sortDirection: 'desc' }));
  assert.equal(url.pathname, `/api/query-results/${ID}/table`);
  assert.deepEqual([url.searchParams.get('page'), url.searchParams.get('page_size'), url.searchParams.getAll('columns')], ['2', '25', ['a', 'b']]);
  assert.deepEqual([url.searchParams.get('search'), url.searchParams.get('sort_column'), url.searchParams.get('sort_direction')], ['part_3', 'a', 'desc']);
  const chartUrl = new URL(api.buildChartUrl({ resultId: ID, chartType: 'line', xColumn: 'm', yColumn: 'q', groupByColumn: 'g', aggregation: 'sum', title: '월별 추이' }));
  assert.deepEqual(Object.fromEntries(chartUrl.searchParams), { chart_type: 'line', x_column: 'm', y_column: 'q', group_by_column: 'g', aggregation: 'sum', title: '월별 추이' });
});

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const flush = () => new Promise((resolve) => setTimeout(resolve, 5));

test('identical in-flight requests share one fetch, but completed results are fetched again', async () => {
  api.clearQueryResultCache();
  let calls = 0; let init;
  globalThis.fetch = async (url, options) => { calls += 1; init = options; return json(chart()); };
  const request = { resultId: ID, chartType: 'area', xColumn: 'm', yColumn: 'q' };
  const first = api.acquireQueryChart(request); const second = api.acquireQueryChart(request);
  assert.equal((await first.promise).chart.type, 'area'); await second.promise;
  assert.equal(calls, 1); assert.equal(init.credentials, 'include');
  first.release(); second.release();
  const next = api.acquireQueryChart(request);
  await next.promise;
  assert.equal(calls, 2);
  next.release();
});

test('failed responses are never cached and retry fetches again', async () => {
  api.clearQueryResultCache();
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return calls === 1 ? json({ detail: { code: 'RESULT_NOT_FOUND', message: 'x' } }, 404) : json(table()); };
  const request = { resultId: ID, page: 1, pageSize: 50 };
  await assert.rejects(api.acquireQueryTable(request).promise, (error) => error.kind === 'not-found' && /만료/.test(error.message));
  assert.equal((await api.acquireQueryTable(request).promise).row_count, 2);
  assert.equal(calls, 2);
});

test('error statuses map to safe kinds and never expose server internals', async () => {
  const cases = [[404, { detail: 'secret path /data/x' }, 'not-found'], [422, { detail: { code: 'COLUMN_NOT_FOUND', message: '컬럼 없음' } }, 'invalid-request'], [500, { detail: 'Traceback' }, 'network']];
  for (const [status, body, kind] of cases) {
    api.clearQueryResultCache();
    globalThis.fetch = async () => json(body, status);
    await assert.rejects(api.fetchQueryTable({ resultId: ID, page: 1, pageSize: 50 }), (error) => error.kind === kind && !/secret|Traceback|\/data/.test(error.message));
  }
  globalThis.fetch = async () => new Response('not json', { status: 200 });
  await assert.rejects(api.fetchQueryTable({ resultId: ID, page: 1, pageSize: 50 }), (error) => error.kind === 'invalid-response');
  globalThis.fetch = async () => json({ status: 'ok', rows: 'x' });
  await assert.rejects(api.fetchQueryChart({ resultId: ID, chartType: 'bar', xColumn: 'a', yColumn: 'b' }), (error) => error.kind === 'invalid-response');
  globalThis.fetch = async () => { throw new TypeError('offline'); };
  await assert.rejects(api.fetchQueryTable({ resultId: ID, page: 1, pageSize: 50 }), (error) => error.kind === 'network');
});

test('releasing the last subscriber aborts the underlying request', async () => {
  api.clearQueryResultCache();
  let aborted = false;
  globalThis.fetch = (url, { signal }) => new Promise((resolve, reject) => { signal.addEventListener('abort', () => { aborted = true; reject(new DOMException('aborted', 'AbortError')); }); });
  const request = api.acquireQueryTable({ resultId: ID, page: 3, pageSize: 10 });
  const settled = request.promise.catch((error) => error.kind);
  request.release(); await flush();
  assert.equal(aborted, true); assert.equal(await settled, 'aborted');
});

/* ---------------- 메시지 변환: present는 standalone, 순서·실패 정책 ---------------- */

const tool = (id, name, args, result) => ({ kind: 'tool', id, toolCallId: id, toolName: name, args, ...(result ? { result: { id, toolCallId: id, toolName: name, data: result } } : {}) });
const assistant = (parts) => ({ id: 'a', role: 'assistant', content: '', parts, statuses: [], runState: { type: 'complete' } });
const text = (id, value) => ({ kind: 'text', id, text: value });
const contentTypes = (m) => convertMessage(m).content.map((p) => p.type === 'text' ? `text:${p.text}` : `${p.toolName}:${p.toolCallId}`);

test('present_table is a standalone tool and keeps its text context order after regular tools', () => {
  assert.equal(standalone.isStandaloneTool('present_table'), true);
  const m = assistant([
    text('t0', '조회합니다.'), tool('sql', 'execute_sql', { sql: 'S' }, { status: 'ok', result_id: ID }),
    text('t1', '결과를 보여드립니다.'), tool('p', 'present_table', { result_id: ID }, {}), text('t2', '표에는 두 건이 있습니다.'),
  ]);
  assert.deepEqual(contentTypes(m), ['execute_sql:sql', 'text:결과를 보여드립니다.', 'present_table:p', 'text:표에는 두 건이 있습니다.']);
});

test('a failed present_table is hidden once a later present_table succeeds; all-failed keeps the error surface', () => {
  const failed = tool('p1', 'present_table', { result_id: ID }, { status: 'error', code: 'COLUMN_NOT_FOUND', message: '컬럼 없음' });
  const ok = tool('p2', 'present_table', { result_id: ID }, {});
  assert.deepEqual(contentTypes(assistant([failed, ok])).filter((x) => x.startsWith('present_table')), ['present_table:p2']);
  assert.deepEqual(contentTypes(assistant([failed])).filter((x) => x.startsWith('present_table')), ['present_table:p1']);
  assert.equal(convertMessage(assistant([failed])).content[0].isError, true);
});

/* ---------------- present preview 결과 shape ---------------- */

const html = (Component, data) => renderToStaticMarkup(createElement(Component, { data }));

test('DatabaseResult renders present preview without full rows', () => {
  const preview = { status: 'ok', kind: 'database', result_id: ID, row_count: 250, source_truncated: false, columns: [{ name: 'work_month', dtype: 'str', role: 'time' }, { name: 'qty', dtype: 'int64', role: 'measure' }, { name: 'line', dtype: 'str', role: 'category' }],
    sample_rows: [{ work_month: '2026-01', qty: 10, line: 'A' }], date_ranges: { work_month: { min: '2026-01', max: '2026-12' } }, distinct_counts: { work_month: 12, line: 2 }, statistics: { qty: { min: 1, max: 40, avg: 20, sum: 5000, null_count: 0 } }, top_groups: { line: [{ value: 'A', count: 120 }] } };
  const out = html(DatabaseResult, preview);
  assert.match(out, /250/); assert.match(out, /2026-01/); assert.match(out, /min 1 · max 40 · 평균 20/); assert.match(out, /2026-12/); assert.match(out, /고유값 2개/);
  assert.match(html(DatabaseResult, { ...preview, row_count: 0, sample_rows: [], statistics: {} }), /0건/);
  assert.match(html(DatabaseResult, { table: { columns: ['part'], rows: [['part_1']] } }), /part_1/);
});

test('SimulationResult shows KPIs, summary and preview for present payloads', () => {
  const out = html(SimulationResult, { status: 'ok', kind: 'simulation', result_id: ID, scenario: 'HVLM', summary: '요약 문장', kpis: [{ label: 'Part', value: 0, unit: '개' }], row_count: 11, columns: [{ name: 'table', dtype: 'str', role: 'category' }], sample_rows: [{ table: 'part' }], statistics: {}, distinct_counts: {}, date_ranges: {}, top_groups: {} });
  assert.match(out, />0</); assert.match(out, /요약 문장/); assert.match(out, /HVLM/); assert.match(out, /전체/);
});

test('area charts are supported with an accessible textual summary', () => {
  const spec = chart().chart;
  assert.match(chartSummary(spec), /영역 차트/);
  const out = renderToStaticMarkup(createElement(ChartBlock, { chart: spec, warnings: chart().warnings, alwaysLegend: true }));
  assert.match(out, /영역 차트/); assert.match(out, /차트 데이터 표로 보기/); assert.match(out, /저장된 조회 결과 범위 안내/);
});

test('stacked bar charts identify the cumulative display in their accessible summary', () => {
  const spec = { ...chart().chart, type: 'bar', title: null };
  assert.match(chartSummary(spec, true), /누적 막대 차트/);
  const out = renderToStaticMarkup(createElement(ChartBlock, { chart: spec, stacked: true, alwaysLegend: true }));
  assert.match(out, /aria-label="누적 막대 차트"/);
  assert.match(out, /누적 막대 차트/);
});

test('Y-axis tick labels use compact K/M/B notation while preserving small values and signs', () => {
  assert.equal(formatYAxisTick(10), '10');
  assert.equal(formatYAxisTick(1_000), '1K');
  assert.equal(formatYAxisTick(10_000), '10K');
  assert.equal(formatYAxisTick(1_000_000), '1M');
  assert.equal(formatYAxisTick(25_000_000), '25M');
  assert.equal(formatYAxisTick(1_200_000_000), '1.2B');
  assert.equal(formatYAxisTick(-1_250_000), '-1.3M');
  assert.equal(formatYAxisTick(1.234), '1.234');
  assert.equal(formatYAxisTick('not-a-number'), 'not-a-number');
});

test('only a valid successful present_table suppresses Markdown tables in its own answer', () => {
  const prose = '결론입니다.\n\n| 지표 | 값 |\n| --- | --- |\n| 수량 | 20 |\n\n근거입니다.';
  const success = tool('p', 'present_table', { result_id: ID }, {});
  const pending = tool('p', 'present_table', { result_id: ID });
  const failed = tool('p', 'present_table', { result_id: ID }, { status: 'error', message: '실패' });
  const malformed = tool('p', 'present_table', { result_id: 'invalid' }, {});
  for (const [part, hidden] of [[success, true], [pending, false], [failed, false], [malformed, false], [tool('c', 'present_chart', { result_id: ID }, {}), false]]) {
    const converted = convertMessage(assistant([text('before', prose), part, text('after', prose)]));
    assert.equal(converted.metadata.custom.hideMarkdownTables, hidden);
    assert.deepEqual(converted.content.filter(p => p.type === 'text').map(p => p.text), [prose, prose]);
  }
  assert.equal(convertMessage(assistant([text('only', prose)])).metadata.custom.hideMarkdownTables, false);
  assert.equal(convertMessage({ id: 'u', role: 'user', content: prose }).content[0].text, prose);
});

test('table keeps the last page of the same result while a new search or sort loads', async () => {
  // 검색어를 입력하면 표 전체가 "불러오는 중"으로 바뀌어 검색창이 다시 그려지고 포커스를 잃었다.
  const { displayedTablePage } = await server.ssrLoadModule('/src/components/chat/generative/displayed-table-page.ts');
  const page = table();
  const last = { resultId: ID, requestBaseKey: 'old-search', value: page };
  assert.equal(displayedTablePage({ type: 'loading' }, last, ID, 'new-search'), page);
  assert.equal(displayedTablePage({ type: 'loading' }, { ...last, resultId: 'b'.repeat(32) }, ID, 'new-search'), null);
  assert.equal(displayedTablePage({ type: 'error' }, last, ID, 'new-search'), null);
  assert.equal(displayedTablePage({ type: 'error' }, last, ID, 'old-search'), page);
  const fresh = table({ page: 2 });
  assert.equal(displayedTablePage({ type: 'success', value: fresh }, last, ID, 'new-search'), fresh);
});

test('line charts mark each point only while points stay readable', async () => {
  // 6개월 추이에 점이 없어 각 달의 값을 읽기 어려웠다. 계열당 최대 500포인트라 많을 때는 점을 숨긴다.
  const { lineDot, LINE_DOT_MAX_POINTS } = await server.ssrLoadModule('/src/components/chat/tool-results/charts/chart-style.ts');
  assert.equal(lineDot(6).r, 3);
  assert.equal(lineDot(LINE_DOT_MAX_POINTS).strokeDasharray, '0');
  assert.equal(lineDot(LINE_DOT_MAX_POINTS + 1), false);
});
