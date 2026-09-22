import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let server, suggestions, state, runtime, threads, toolkitModule;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  suggestions = await server.ssrLoadModule('/src/lib/suggestions.ts');
  state = await server.ssrLoadModule('/src/lib/chat-state.ts');
  runtime = await server.ssrLoadModule('/src/lib/chat-runtime.ts');
  threads = await server.ssrLoadModule('/src/lib/agent-threads.ts');
  toolkitModule = await server.ssrLoadModule('/src/components/chat/toolkit/index.tsx');
});
after(async () => { await server.close(); });

test('suggestions accept only 2-4 unique short strings and never guess', () => {
  const parse = suggestions.parseSuggestions;
  assert.deepEqual(parse([' 하나 ', '둘']), ['하나', '둘']);
  assert.deepEqual(parse(['a', 'a', 'b']), ['a', 'b']);
  for (const bad of [undefined, null, 'x', [], ['하나'], ['a', 'b', 'c', 'd', 'e'], ['a', 1], ['a', ''], ['a', 'x'.repeat(121)], ['a', 'a'], [['a'], 'b']]) assert.equal(parse(bad), undefined);
});

const base = () => ({ id: 'a', role: 'assistant', content: '', parts: [], statuses: [], runState: { type: 'running' } });

test('only a successful done carries suggestions into the run result', () => {
  const ok = state.applyAgentEvent(base(), { type: 'done', data: { turn_id: 'T1', suggestions: ['가', '나'] } }, 'p');
  assert.deepEqual(ok.suggestions, ['가', '나']);
  assert.deepEqual(runtime.toRunResult(ok).metadata.custom.suggestions, ['가', '나']);
  const errored = state.applyAgentEvent(state.applyAgentEvent(base(), { type: 'error', content: 'x' }, 'p'), { type: 'done', data: { suggestions: ['가', '나'] } }, 'q');
  assert.equal(errored.suggestions, undefined);
  const malformed = state.applyAgentEvent(base(), { type: 'done', data: { turn_id: 'T', suggestions: ['가'] } }, 'p');
  assert.equal(malformed.suggestions, undefined);
});

test('suggestion adapter reads only the last completed assistant message', async () => {
  const gen = (messages) => threads.suggestionAdapter.generate({ messages });
  const done = { role: 'assistant', status: { type: 'complete' }, metadata: { custom: { suggestions: ['가', '나'] } } };
  assert.deepEqual(await gen([done]), [{ prompt: '가' }, { prompt: '나' }]);
  assert.deepEqual(await gen([{ ...done, status: { type: 'incomplete', reason: 'cancelled' } }]), []);
  assert.deepEqual(await gen([done, { role: 'user', metadata: { custom: {} } }]), []);
  assert.deepEqual(await gen([{ ...done, metadata: { custom: {} } }]), []);
});

test('toolkit registers every Backend tool of both result UI modes', () => {
  const expected = ['execute_sql', 'search_documents', 'list_simulation', 'run_simulation', 'list_tables', 'describe_table', 'list_kpis', 'get_kpi', 'list_recipes', 'get_recipe', 'get_result_summary', 'get_result_page', 'prepare_table', 'prepare_visualization', 'present'];
  assert.deepEqual(Object.keys(toolkitModule.productionPlanningToolkit).sort(), expected.sort());
  for (const name of ['present', 'prepare_table', 'prepare_visualization']) assert.equal(toolkitModule.productionPlanningToolkit[name].display, 'standalone', name);
  for (const name of toolkitModule.GROUPED_TOOL_NAMES) assert.notEqual(toolkitModule.productionPlanningToolkit[name].display, 'standalone', name);
});
