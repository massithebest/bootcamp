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
    { type: 'tool_call', tool_name: 'execute_sql' },
    { type: 'tool_result', tool_name: 'execute_sql', data: { purpose: 'WIP 확인', status: 'ok' } },
    { type: 'status', data: { step: 'execute_sql', status: 'completed' } },
    { type: 'tool_call', tool_name: 'run_simulation' },
    { type: 'status', data: { step: 'run_simulation', status: 'error' } },
    { type: 'text', content: '답변' }, { type: 'done', data: { turn_id: 't1' } },
  ];
  events.forEach((event, i) => { current = applyAgentEvent(current, event, String(i)); });
  assert.deepEqual(initial, message());
  assert.deepEqual(current.parts.map(p => p.kind), ['text', 'tool', 'text']);
  assert.equal(current.parts[0].text, '앞말');
  assert.equal(current.statuses[0].detail, 'WIP 확인');
  assert.deepEqual(current.statuses.map(s => s.status), ['completed', 'error']);
  assert.equal(current.turnId, 't1');
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
