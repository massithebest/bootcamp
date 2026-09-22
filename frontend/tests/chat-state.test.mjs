import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';
let server, applyAgentEvent, convertMessage, toolResultError;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  ({ applyAgentEvent } = await server.ssrLoadModule('/src/lib/chat-state.ts'));
  ({ convertMessage } = await server.ssrLoadModule('/src/lib/chat-runtime.ts'));
  ({ toolResultError } = await server.ssrLoadModule('/src/lib/tool-result.ts'));
});
after(async () => server.close());
const message = () => ({ id: 'assistant', role: 'assistant', content: '', parts: [], statuses: [], runState: { type: 'running' } });
test('immutable text/tool/text and multiple tool status transitions', () => {
  const initial = message();
  let current = initial;
  const events = [
    { type: 'text', content: '앞' }, { type: 'text', content: '말' },
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'call-sql', data: { args: { sql: 'SELECT 1' } } },
    { type: 'tool_result', tool_name: 'execute_sql', tool_call_id: 'call-sql', data: { purpose: 'WIP 확인', status: 'ok' } },
    { type: 'status', tool_name: 'execute_sql', tool_call_id: 'call-sql', data: { step: 'call-sql', status: 'completed' } },
    { type: 'tool_call', tool_name: 'run_simulation', tool_call_id: 'call-sim', data: { args: { dataset: 'LVHM' } } },
    { type: 'status', tool_name: 'run_simulation', tool_call_id: 'call-sim', data: { step: 'call-sim', status: 'error' } },
    { type: 'text', content: '답변' }, { type: 'done', data: { turn_id: 't1' } },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, String(i)); });
  assert.deepEqual(initial, message());
  assert.deepEqual(current.parts.map(p => p.kind), ['text', 'tool', 'tool', 'text']);
  assert.equal(current.parts[0].text, '앞말');
  assert.deepEqual(current.parts[1].args, { sql: 'SELECT 1' });
  assert.deepEqual(current.parts[2].args, { dataset: 'LVHM' });
  assert.equal(current.statuses[0].detail, 'WIP 확인');
  assert.deepEqual(current.statuses.map(s => s.status), ['completed', 'error']);
  assert.equal(current.turnId, 't1');

  const rendered = convertMessage(current);
  assert.deepEqual(rendered.content.map(part => part.type), ['tool-call', 'tool-call', 'text']);
  assert.equal(rendered.content.at(-1).text, '답변');
  assert.ok(!JSON.stringify(rendered.content).includes('앞말'));
  assert.deepEqual(rendered.metadata.custom.statuses, [], 'tool statuses must not be duplicated as public status rows');
});

test('independent public status is exposed through assistant metadata', () => {
  let current = message();
  current = applyAgentEvent(current, {
    type: 'status',
    data: { step: 'plan', label: '질의 분석', detail: '조회 범위 확인', status: 'running' },
  }, 'status');

  assert.deepEqual(convertMessage(current).metadata.custom.statuses, [{
    step: 'plan',
    label: '질의 분석',
    detail: '조회 범위 확인',
    status: 'running',
  }]);
});

test('latest public pre-tool text remains only while its tool is running', () => {
  let current = message();
  current = applyAgentEvent(current, { type: 'text', content: 'WIP 조회 조건을 확인합니다.' }, 'plan-1');
  current = applyAgentEvent(current, {
    type: 'tool_call', tool_name: 'list_tables', tool_call_id: 'tables', data: { args: { keyword: 'wip' } },
  }, 'tool-1');

  let rendered = convertMessage(current);
  assert.equal(rendered.metadata.custom.progressText, 'WIP 조회 조건을 확인합니다.');
  assert.ok(!rendered.content.some(part => part.type === 'text'));

  current = applyAgentEvent(current, {
    type: 'tool_result', tool_name: 'list_tables', tool_call_id: 'tables', data: { status: 'ok' },
  }, 'result-1');
  assert.equal(convertMessage(current).metadata.custom.progressText, undefined);

  current = applyAgentEvent(current, { type: 'text', content: 'WIP 테이블 구조를 확인합니다.' }, 'plan-2');
  rendered = convertMessage(current);
  assert.equal(rendered.metadata.custom.progressText, undefined);
  assert.equal(rendered.content.at(-1).text, 'WIP 테이블 구조를 확인합니다.');

  current = applyAgentEvent(current, {
    type: 'tool_call', tool_name: 'describe_table', tool_call_id: 'describe', data: { args: { table: 'wip' } },
  }, 'tool-2');
  rendered = convertMessage(current);
  assert.equal(rendered.metadata.custom.progressText, 'WIP 테이블 구조를 확인합니다.');

  current = applyAgentEvent(current, { type: 'done' }, 'done');
  assert.equal(convertMessage(current).metadata.custom.progressText, undefined);
});

test('repeated tool names pair parameters and results by tool_call_id', () => {
  let current = message();
  const events = [
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql-1', data: { args: { sql: 'SELECT 1' } } },
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql-2', data: { args: { sql: 'SELECT 2' } } },
    { type: 'tool_result', tool_name: 'execute_sql', tool_call_id: 'sql-2', data: { rows: [[2]] } },
    { type: 'tool_result', tool_name: 'execute_sql', tool_call_id: 'sql-1', data: { rows: [[1]] } },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, `part-${i}`); });

  assert.deepEqual(current.parts.map(part => part.toolCallId), ['sql-1', 'sql-2']);
  assert.deepEqual(current.parts.map(part => part.args.sql), ['SELECT 1', 'SELECT 2']);
  assert.deepEqual(current.parts.map(part => part.result.data.rows[0][0]), [1, 2]);
});

test('standalone chart preserves its position before the following explanation', () => {
  let current = message();
  const resultId = 'b'.repeat(32);
  const events = [
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql', data: { args: {} } },
    { type: 'tool_result', tool_name: 'execute_sql', tool_call_id: 'sql', data: { status: 'ok' } },
    { type: 'tool_call', tool_name: 'present_chart', tool_call_id: 'chart', data: { args: { result_id: resultId } } },
    { type: 'tool_result', tool_name: 'present_chart', tool_call_id: 'chart', data: { status: 'ok', result_id: resultId } },
    { type: 'text', content: '최종 설명' },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, `visual-${i}`); });

  const rendered = convertMessage(current).content;
  assert.deepEqual(rendered.map(part => part.type), ['tool-call', 'tool-call', 'text']);
  assert.equal(rendered[1].toolName, 'present_chart');
  assert.equal(rendered[1].result.data.result_id, resultId);
});

test('standalone table preserves its position before the following explanation', () => {
  let current = message();
  const resultId = 'd'.repeat(32);
  const events = [
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql', data: { args: {} } },
    { type: 'tool_result', tool_name: 'execute_sql', tool_call_id: 'sql', data: { status: 'ok' } },
    { type: 'tool_call', tool_name: 'present_table', tool_call_id: 'table', data: { args: { result_id: resultId } } },
    { type: 'tool_result', tool_name: 'present_table', tool_call_id: 'table', data: { status: 'ok', result_id: resultId } },
    { type: 'text', content: '최종 설명' },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, `table-${i}`); });

  const rendered = convertMessage(current).content;
  assert.deepEqual(rendered.map(part => part.type), ['tool-call', 'tool-call', 'text']);
  assert.equal(rendered[1].toolName, 'present_table');
  assert.equal(rendered[1].result.data.result_id, resultId);
});

test('table, chart, and their explanations keep the AgentEvent sequence', () => {
  let current = message();
  const resultId = 'f'.repeat(32);
  const events = [
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql', data: { args: {} } },
    { type: 'tool_result', tool_name: 'execute_sql', tool_call_id: 'sql', data: { status: 'ok' } },
    { type: 'text', content: '표에서 제품별 수량을 먼저 확인할 수 있습니다.' },
    { type: 'tool_call', tool_name: 'present_table', tool_call_id: 'table', data: { args: { result_id: resultId } } },
    { type: 'tool_result', tool_name: 'present_table', tool_call_id: 'table', data: { status: 'ok', result_id: resultId } },
    { type: 'text', content: 'A 제품이 20개입니다. 같은 결과의 분포를 차트로 비교합니다.' },
    { type: 'tool_call', tool_name: 'present_chart', tool_call_id: 'chart', data: { args: { result_id: resultId } } },
    { type: 'tool_result', tool_name: 'present_chart', tool_call_id: 'chart', data: { status: 'ok', result_id: resultId } },
    { type: 'text', content: '차트에서도 A 제품이 가장 큽니다.' },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, `context-${i}`); });

  const rendered = convertMessage(current).content;
  assert.deepEqual(
    rendered.map(part => part.type === 'tool-call' ? `${part.type}:${part.toolName}` : part.type),
    ['tool-call:execute_sql', 'text', 'tool-call:present_table', 'text', 'tool-call:present_chart', 'text'],
  );
  assert.deepEqual(rendered.filter(part => part.type === 'text').map(part => part.text), [
    '표에서 제품별 수량을 먼저 확인할 수 있습니다.',
    'A 제품이 20개입니다. 같은 결과의 분포를 차트로 비교합니다.',
    '차트에서도 A 제품이 가장 큽니다.',
  ]);
});

test('a corrected chart failure is hidden when the same result later succeeds', () => {
  let current = message();
  const resultId = 'result-1';
  const events = [
    { type: 'tool_call', tool_name: 'present_chart', tool_call_id: 'chart-failed', data: { args: { result_id: resultId } } },
    { type: 'tool_result', tool_name: 'present_chart', tool_call_id: 'chart-failed', data: { status: 'error', message: 'group_by 오류' } },
    { type: 'tool_call', tool_name: 'present_chart', tool_call_id: 'chart-success', data: { args: { result_id: resultId } } },
    { type: 'tool_result', tool_name: 'present_chart', tool_call_id: 'chart-success', data: { status: 'ok', result_id: resultId } },
    { type: 'text', content: '보정 완료' },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, `corrected-${i}`); });

  const chartParts = convertMessage(current).content.filter(
    part => part.type === 'tool-call' && part.toolName === 'present_chart',
  );
  assert.equal(chartParts.length, 1);
  assert.equal(chartParts[0].toolCallId, 'chart-success');
});
for (const type of ['error', 'cancelled', 'complete']) test(`done preserves ${type} lifecycle`, () => {
  const m = { ...message(), runState: type === 'error' ? { type, message: '오류' } : { type } };
  const result = applyAgentEvent(m, { type: 'done' }, 'end');
  assert.deepEqual(result.runState, m.runState);
  assert.equal(convertMessage(result).status.type, type === 'complete' ? 'complete' : 'incomplete');
});
for (const data of [{ status: 'error' }, { error: true }, { error: '실패' }]) test(`tool error agrees with runtime: ${JSON.stringify(data)}`, () => {
  const m = applyAgentEvent(message(), { type: 'tool_result', tool_name: 'execute_sql', data }, 'tool');
  assert.ok(toolResultError(m.parts[0].result));
  assert.equal(convertMessage(m).content[0].isError, true);
});

test('later execution tools preserve earlier standalone results and their context', () => {
  let current = message();
  const events = [
    { type: 'text', content: '조회 준비' },
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql-1' },
    { type: 'text', content: '첫 결과의 분포입니다.' },
    { type: 'tool_call', tool_name: 'present_chart', tool_call_id: 'chart' },
    { type: 'tool_result', tool_name: 'present_chart', tool_call_id: 'chart', data: { status: 'ok', result_id: 'a'.repeat(32) } },
    { type: 'text', content: '차트를 설명하고 추가 데이터를 조회합니다.' },
    { type: 'tool_call', tool_name: 'execute_sql', tool_call_id: 'sql-2' },
    { type: 'text', content: '두 번째 결과입니다.' },
    { type: 'tool_call', tool_name: 'present_table', tool_call_id: 'table' },
    { type: 'tool_result', tool_name: 'present_table', tool_call_id: 'table', data: { status: 'ok', result_id: 'b'.repeat(32) } },
    { type: 'text', content: '표의 해석입니다.' },
    { type: 'tool_call', tool_name: 'get_result_summary', tool_call_id: 'summary' },
    { type: 'text', content: '최종 결론입니다.' },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, `later-${i}`); });
  const parts = convertMessage(current).content;
  assert.deepEqual(parts.map(part => part.type === 'text' ? part.text : part.toolCallId), [
    'sql-1', 'sql-2', 'summary', '첫 결과의 분포입니다.', 'chart',
    '차트를 설명하고 추가 데이터를 조회합니다.', '두 번째 결과입니다.', 'table',
    '표의 해석입니다.', '최종 결론입니다.',
  ]);
});
