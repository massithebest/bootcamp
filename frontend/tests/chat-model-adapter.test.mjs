import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let server, adapterModule, threads, EventQueue;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  adapterModule = await server.ssrLoadModule('/src/lib/chat-model-adapter.ts');
  threads = await server.ssrLoadModule('/src/lib/agent-threads.ts');
  ({ EventQueue } = await server.ssrLoadModule('/src/lib/event-queue.ts'));
});
after(async () => { await server.close(); });

const user = (text) => ({ role: 'user', content: [{ type: 'text', text }] });
const assistant = (turnId) => ({ role: 'assistant', content: [{ type: 'text', text: 'a' }], metadata: { custom: turnId ? { turnId } : {} } });

/* ---------------- fork 규칙: 분기 경로의 anchor와 대화 head ---------------- */

test('planTurn chooses continue / fork / restart from the branch path and the conversation head', () => {
  const plan = (messages, head) => adapterModule.planTurn(messages, { headTurnId: head });
  const cases = [
    ['first turn continues the (empty) session', [user('q1')], undefined, undefined],
    ['next turn after the head continues', [user('q1'), assistant('T1'), user('q2')], 'T1', undefined],
    ['editing the first question restarts from scratch', [user('q1 edited')], 'T1', ''],
    ['regenerate/edit a later question forks at the previous turn', [user('q1'), assistant('T1'), user('q2')], 'T2', 'T1'],
    ['continuing an older branch forks at that branch turn', [user('q1'), assistant('T1'), user('q2'), assistant('T2'), user('q3')], 'T3', 'T2'],
    ['a failed previous answer falls back to the nearest successful turn', [user('q1'), assistant('T1'), user('q2'), assistant(undefined), user('q3')], 'T1', undefined],
    ['no successful turn on this path but the conversation has one restarts', [user('q1'), assistant(undefined), user('q2')], 'T9', ''],
    ['no turns anywhere continues', [user('q1'), assistant(undefined), user('q2')], undefined, undefined],
  ];
  for (const [name, messages, head, expected] of cases) assert.equal(plan(messages, head).forkFromTurnId, expected, name);
});

test('planTurn rejects paths without a sendable user message', () => {
  assert.equal(adapterModule.planTurn([], {}), null);
  assert.equal(adapterModule.planTurn([assistant('T1')], {}), null);
  assert.equal(adapterModule.planTurn([user('   ')], {}), null);
  assert.equal(adapterModule.planTurn([{ role: 'user', content: '문자열 본문' }], {}).text, '문자열 본문');
});

/* ---------------- ChatModelAdapter.run ---------------- */

const fast = { frame: async () => {}, now: (() => { let t = 0; return () => (t += 10); })() };
async function collect(events, { conversation = adapterModule.createConversation('conv-1'), messages = [user('질문')], signal = new AbortController().signal, outcome = 'complete', hold } = {}) {
  const calls = [];
  const adapter = adapterModule.createAgentChatAdapter(conversation, {
    ...fast,
    sendChatMessage: async (options) => {
      calls.push({ message: options.message, conversationId: options.conversationId, forkFromTurnId: options.forkFromTurnId, hasSignal: !!options.signal });
      for (const event of events) { await Promise.resolve(); options.onEvent(event); }
      if (hold) await hold;
      return outcome;
    },
  });
  const results = [];
  for await (const result of adapter.run({ messages, abortSignal: signal, runConfig: {}, context: {} })) results.push(result);
  return { results, calls, conversation };
}
const call = (id, name, args) => ({ type: 'tool_call', tool_name: name, tool_call_id: id, data: { args } });
const result = (id, name, data) => ({ type: 'tool_result', tool_name: name, tool_call_id: id, data });

test('streams cumulative snapshots and finishes complete with the turn id as the new head', async () => {
  const { results, calls, conversation } = await collect([
    { type: 'text', content: '조회' }, { type: 'text', content: '합니다.' },
    call('sql', 'execute_sql', { sql: 'S' }), result('sql', 'execute_sql', { status: 'ok', result_id: 'a'.repeat(32) }),
    call('p', 'present_table', { result_id: 'a'.repeat(32) }), result('p', 'present_table', {}),
    { type: 'text', content: '표에는 결과가 있습니다.' }, { type: 'done', data: { turn_id: 'T1' } },
  ]);
  assert.deepEqual(calls, [{ message: '질문', conversationId: 'conv-1', forkFromTurnId: undefined, hasSignal: true }]);
  const last = results.at(-1);
  assert.deepEqual(last.status, { type: 'complete', reason: 'stop' });
  assert.deepEqual(last.content.map((p) => (p.type === 'text' ? 'text' : p.toolName)), ['execute_sql', 'present_table', 'text']);
  assert.deepEqual(last.content.filter((p) => p.type === 'tool-call').map((p) => [p.toolName, p.result !== undefined]), [['execute_sql', true], ['present_table', true]]);
  assert.equal(last.metadata.custom.turnId, 'T1');
  assert.ok(Array.isArray(last.metadata.custom.statuses) && last.metadata.custom.observedTiming.endedAt >= last.metadata.custom.observedTiming.startedAt);
  assert.equal(conversation.headTurnId, 'T1');
  const running = results.filter((r) => r.status.type === 'running');
  assert.ok(running.length >= 1, 'intermediate snapshots are running');
  assert.ok(results.length >= 2);
});

test('forks are sent from the planned anchor and the head moves to the new turn', async () => {
  const conversation = adapterModule.createConversation('conv-2'); conversation.headTurnId = 'T2';
  const { calls } = await collect([{ type: 'text', content: '답' }, { type: 'done', data: { turn_id: 'T3' } }], { conversation, messages: [user('q1'), assistant('T1'), user('q2 edited')] });
  assert.equal(calls[0].forkFromTurnId, 'T1');
  assert.equal(conversation.headTurnId, 'T3');
});

test('backend error then done ends incomplete/error and keeps the previous head', async () => {
  const conversation = adapterModule.createConversation('conv-3'); conversation.headTurnId = 'T1';
  const { results } = await collect([{ type: 'text', content: '부분' }, { type: 'error', content: '안전한 오류' }, { type: 'done' }], { conversation, messages: [user('q1'), assistant('T1'), user('q2')] });
  const last = results.at(-1);
  assert.equal(last.status.type, 'incomplete'); assert.equal(last.status.reason, 'error'); assert.equal(last.status.error, '안전한 오류');
  assert.equal(last.content[0].text, '부분');
  assert.equal(conversation.headTurnId, 'T1');
  assert.equal(last.metadata.custom.turnId, undefined);
});

test('a transport failure without output still ends as an error message (reload is the retry)', async () => {
  const { results } = await collect([{ type: 'error', content: 'Backend 에 연결하지 못했습니다.' }, { type: 'done' }], { outcome: 'failed' });
  assert.equal(results.at(-1).status.reason, 'error');
  assert.deepEqual(results.at(-1).content, []);
});

test('a stream that never sends done is closed as an error instead of staying running', async () => {
  const { results } = await collect([{ type: 'text', content: '중간' }]);
  assert.equal(results.at(-1).status.type, 'incomplete');
});

test('abort stops without a terminal snapshot and does not advance the head', async () => {
  const controller = new AbortController();
  const conversation = adapterModule.createConversation('conv-4');
  let release; const hold = new Promise((resolve) => { release = resolve; });
  const adapter = adapterModule.createAgentChatAdapter(conversation, { ...fast, sendChatMessage: async ({ onEvent, signal }) => {
    onEvent({ type: 'text', content: '진행 중' });
    await new Promise((resolve) => signal.addEventListener('abort', resolve, { once: true }));
    return 'aborted';
  } });
  const results = [];
  const finished = (async () => { for await (const r of adapter.run({ messages: [user('q')], abortSignal: controller.signal, runConfig: {}, context: {} })) { results.push(r); controller.abort(); } })();
  await finished; release?.(); void hold;
  assert.equal(results.length, 1);
  assert.equal(results[0].status.type, 'running');
  assert.equal(conversation.headTurnId, undefined);
});

/* ---------------- 보조 모듈 ---------------- */

test('EventQueue hands over bursts as batches and drains after close', async () => {
  const queue = new EventQueue();
  queue.push(1); queue.push(2);
  const seen = [];
  const consumer = (async () => { for await (const batch of queue.batches()) seen.push(batch); })();
  await Promise.resolve(); queue.push(3); queue.close(); queue.push(4);
  await consumer;
  assert.deepEqual(seen.flat(), [1, 2, 3]);
});

test('thread titles come from the first question without a model call', () => {
  assert.equal(threads.titleFromMessages([user('  제품별   WIP를 보여줘 ')]), '제품별 WIP를 보여줘');
  assert.equal(threads.titleFromMessages([assistant('T'), user('a'.repeat(60))]).length, threads.TITLE_MAX_LENGTH);
  assert.equal(threads.titleFromMessages([]), '');
});

test('history keeps a thread transcript with parent links and supports update/delete', async () => {
  threads.resetAgentThreads();
  const history = threads.createMemoryHistory('thread-a');
  const u = { message: { id: 'u1', role: 'user' }, parentId: null };
  const a = { message: { id: 'a1', role: 'assistant', v: 1 }, parentId: 'u1' };
  await history.append(u); await history.append(a); await history.update({ ...a, message: { ...a.message, v: 2 } });
  const loaded = await history.load();
  assert.deepEqual(loaded.messages.map((m) => [m.message.id, m.parentId, m.message.v]), [['u1', null, undefined], ['a1', 'u1', 2]]);
  assert.equal(loaded.headId, 'a1');
  assert.deepEqual((await threads.createMemoryHistory('thread-b').load()).messages, []);
  await history.delete([a]);
  assert.equal((await history.load()).messages.length, 1);
  assert.equal(threads.conversationFor('x'), threads.conversationFor('x'));
  assert.notEqual(threads.conversationFor('x').id, threads.conversationFor('y').id);
});
