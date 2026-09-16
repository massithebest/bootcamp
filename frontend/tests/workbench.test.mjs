import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { createServer } from 'vite';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

let server, applyAgentEvent, finishObservedTiming, convertMessage, removeMarkdownTables, executionSummary, formatObservedDuration, DatabaseResult, ChartBlock;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  ({ applyAgentEvent, finishObservedTiming } = await server.ssrLoadModule('/src/lib/chat-state.ts'));
  ({ convertMessage, removeMarkdownTables } = await server.ssrLoadModule('/src/lib/chat-runtime.ts'));
  ({ executionSummary, formatObservedDuration } = await server.ssrLoadModule('/src/lib/execution-summary.ts'));
  ({ DatabaseResult } = await server.ssrLoadModule('/src/components/chat/tool-results/database-result.tsx'));
  ({ ChartBlock } = await server.ssrLoadModule('/src/components/chat/tool-results/chart-block.tsx'));
});
after(async () => server.close());
const message = () => ({ id: 'a', role: 'assistant', content: '', parts: [], statuses: [], runState: { type: 'running' }, observedTiming: { startedAt: 100 } });
const call = id => ({ type: 'tool_call', tool_name: 'execute_sql', tool_call_id: id, data: { args: {} } });
const result = (id, data) => ({ type: 'tool_result', tool_name: 'execute_sql', tool_call_id: id, data });
const zero = { status: 'ok', kind: 'database', row_count: 0, table: { columns: ['qty'], rows: [] } };

test('F01 unrelated, ambiguous and unknown Markdown tables survive; only exact rows match', () => {
  const known = { columns: ['제품', 'WIP'], rows: [['A', 20]] };
  const exact = '| 제품 | WIP |\n| --- | --- |\n| A | 20 |';
  const separate = '| 지표 | 비율 |\n| --- | --- |\n| 불량률 | 2% |';
  assert.equal(removeMarkdownTables(`${exact}\n\n${separate}`, [known]), separate);
  assert.equal(removeMarkdownTables(exact), exact);
  assert.equal(removeMarkdownTables(exact.replace('20', '21'), [known]), exact.replace('20', '21'));
  assert.equal(removeMarkdownTables(exact.replace('20', '**20**'), [known]), exact.replace('20', '**20**'));
  const current = message();
  current.parts = [{ kind: 'text', id: 't', text: separate }, { kind: 'tool', id: 'table', toolCallId: 'table', toolName: 'prepare_table', args: {}, result: {
    id: 'r', toolCallId: 'table', toolName: 'prepare_table', data: { status: 'ok', result_id: 'a'.repeat(32), title: 'WIP', columns: known.columns, rows: known.rows, row_count: 1, displayed_count: 1, source_truncated: false },
  } }];
  assert.equal(convertMessage(current).content[0].text, separate);
});

for (const [name, events, expected] of [
  ['tool-error-done', [call('1'), result('1', { status: 'error', message: '조건 확인' }), { type: 'text', content: '확인 필요' }, { type: 'done' }], [1, 0]],
  ['missing-result', [call('1'), { type: 'done' }], [0, 1]],
  ['empty-done', [{ type: 'done' }], [0, 0]],
  ['zero-rows', [call('1'), result('1', zero), { type: 'done' }], [0, 0]],
  ['error-done', [{ type: 'error', content: '업무 오류' }, { type: 'done' }], [0, 0]],
  ['parallel-reversed', [call('1'), call('2'), result('2', zero), result('1', { status: 'error' }), { type: 'done' }], [1, 0]],
  ['recovered-tool-error', [call('1'), result('1', { status: 'error' }), call('2'), result('2', zero), { type: 'text', content: '조건 수정 후 0건' }, { type: 'done' }], [1, 0]],
]) {
  test(`F02/F12 wire scenario: ${name}`, () => {
    const current = events.reduce((m, e, i) => applyAgentEvent(m, e, `${i}`, 200 + i * 100), message());
    const converted = convertMessage(current);
    const summary = executionSummary(converted.content, false);
    assert.deepEqual([summary.errors, summary.incomplete], expected);
    assert.equal(current.runState.type, name === 'error-done' ? 'error' : 'complete');
    if (name === 'zero-rows') assert.equal(converted.content[0].result.data.row_count, 0);
    if (name === 'parallel-reversed') assert.deepEqual(converted.content.map(p => [p.toolCallId, p.result.data.status]), [['1', 'error'], ['2', 'ok']]);
  });
}

test('F10 monotonic timing is captured per call and freezes on first terminal observation', () => {
  let current = applyAgentEvent(message(), call('1'), '1', 200);
  current = applyAgentEvent(current, call('2'), '2', 400);
  current = applyAgentEvent(current, result('2', zero), '3', 900);
  current = applyAgentEvent(current, result('1', zero), '4', 1200);
  current = applyAgentEvent(current, { type: 'error', content: '종료 오류' }, '5', 1500);
  current = applyAgentEvent(current, { type: 'done' }, '6', 1800);
  assert.deepEqual(current.observedTiming, { startedAt: 100, endedAt: 1500 });
  assert.deepEqual(current.parts.map(p => p.observedTiming), [{ startedAt: 200, endedAt: 1200 }, { startedAt: 400, endedAt: 900 }]);
  assert.equal(convertMessage(current).metadata.custom.toolTimings['2'].endedAt, 900);
  assert.deepEqual(finishObservedTiming(current.observedTiming, 99999), current.observedTiming);
  assert.deepEqual(finishObservedTiming({ startedAt: 100 }, 99), { startedAt: 100, endedAt: 100 });
  assert.equal(formatObservedDuration(400), '1초 미만');
  assert.equal(formatObservedDuration(65000), '1분 5초');
});

test('F10 missing historical timestamps and unmatched tool result are not inferred from IDs', () => {
  const old = { ...message(), observedTiming: undefined };
  let current = applyAgentEvent(old, result('not-observed', zero), 'timestamp-looking-1234', 99999);
  current = applyAgentEvent(current, { type: 'done' }, 'done', 100000);
  assert.equal(current.observedTiming, undefined);
  assert.equal(current.parts[0].observedTiming, undefined);
});

test('F12 zero rows are explicitly different from missing data', () => {
  const empty = renderToStaticMarkup(createElement(DatabaseResult, { data: zero }));
  const missing = renderToStaticMarkup(createElement(DatabaseResult, { data: { status: 'ok' } }));
  assert.match(empty, /조회 결과 0건/);
  assert.match(missing, /조회 데이터가 전달되지/);
  assert.doesNotMatch(missing, /조회 결과 0건/);
});

test('F13 chart exposes a data disclosure without changing axis values', () => {
  const html = renderToStaticMarkup(createElement(ChartBlock, { chart: { type: 'bar', x: 'part', series: [{ key: 'qty', label: 'WIP' }], data: [{ part: 'A', qty: 0 }], categories: ['A'], title: '제품 WIP', x_label: '제품', y_label: '수량', unit: '개' } }));
  assert.match(html, /차트 데이터 표로 보기/);
  assert.match(html, /제품 WIP/);
  assert.match(html, /단위: 개/);
});
