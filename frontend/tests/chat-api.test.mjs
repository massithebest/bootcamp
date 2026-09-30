import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let server;
let sendChatMessage;
const originalFetch = globalThis.fetch;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  ({ sendChatMessage } = await server.ssrLoadModule('/src/lib/chat-api.ts'));
});
after(async () => { globalThis.fetch = originalFetch; await server.close(); });

const frame = (event) => `data: ${JSON.stringify(event)}\r\n\r\n`;
async function collect(text, { split = false, fail = false, signal } = {}) {
  const bytes = new TextEncoder().encode(text);
  let sent = false;
  globalThis.fetch = async () => new Response(new ReadableStream({
    pull(controller) {
      if (sent) { if (fail) controller.error(new Error('fixture')); else controller.close(); return; }
      sent = true;
      if (split) for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
      else controller.enqueue(bytes);
    },
  }), { headers: { 'Content-Type': 'text/event-stream' } });
  const events = [];
  await sendChatMessage({ message: '질문', onEvent: (e) => events.push(e), signal });
  return events;
}

test('UTF-8 byte boundaries, CRLF and ordered text/tool/text survive', async () => {
  const expected = [{ type: 'text', content: '가나다' }, { type: 'tool_result', data: { rows: [[1]] } }, { type: 'text', content: '결과' }, { type: 'done', data: { turn_id: 'turn-1' } }];
  assert.deepEqual(await collect(expected.map(frame).join(''), { split: true }), expected);
});
test('multiple data lines and comments', async () => {
  const events = await collect(': ping\n\ndata: {"type":"text",\ndata: "content":"hello"}\n\n' + frame({ type: 'done' }));
  assert.equal(events[0].content, 'hello');
});
test('backend error then done preserved once', async () => {
  const expected = [{ type: 'error', content: '안전한 오류' }, { type: 'done' }];
  assert.deepEqual(await collect(expected.map(frame).join('')), expected);
});
test('LLM response timeout message is preserved for the error surface', async () => {
  const expected = [
    { type: 'error', content: 'LLM API 서버 응답이 지연되고 있습니다. 잠시 후에 다시 시도해 주세요.' },
    { type: 'done' },
  ];
  assert.deepEqual(await collect(expected.map(frame).join('')), expected);
});
test('EOF without done is incomplete, preserves partial output', async () => {
  const events = await collect(frame({ type: 'text', content: 'partial' }));
  assert.deepEqual(events.map(e => e.type), ['text', 'error', 'done']);
});
test('an unterminated SSE frame cannot publish a successful done', async () => {
  const events = await collect('data: {"type":"done"}');
  assert.deepEqual(events.map(e => e.type), ['error', 'done']);
});
test('done completes even if the server keeps its connection open', async () => {
  let cancelled = false;
  globalThis.fetch = async () => new Response(new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode(frame({ type: 'done' }))); },
    cancel() { cancelled = true; },
  }));
  const outcome = await sendChatMessage({ message: 'q', onEvent() {} });
  assert.equal(outcome, 'complete');
  assert.equal(cancelled, true);
});
test('done is terminal, duplicate and trailing events are ignored', async () => {
  const events = await collect(frame({ type: 'done' }) + frame({ type: 'done' }) + frame({ type: 'text', content: 'late' }));
  assert.deepEqual(events.map(e => e.type), ['done']);
});
for (const payload of ['{', '{"type":"unknown"}', '{"type":"text","content":3}', '{"type":"tool_result","data":[]}', '{"type":"tool_call","tool_call_id":3}']) {
  test(`invalid envelope fails safely: ${payload}`, async () => {
    const events = await collect(`data: ${payload}\n\n` + frame({ type: 'done' }));
    assert.deepEqual(events.map(e => e.type), ['error', 'done']);
  });
}
test('partial stream read failure emits error/done', async () => {
  const events = await collect(frame({ type: 'text', content: 'partial' }), { fail: true });
  assert.deepEqual(events.map(e => e.type), ['text', 'error', 'done']);
});
test('network failure and abort are distinct', async () => {
  const events = [];
  globalThis.fetch = async () => { throw new TypeError('offline'); };
  await sendChatMessage({ message: 'q', onEvent: e => events.push(e) });
  assert.deepEqual(events.map(e => e.type), ['error', 'done']);
  events.length = 0;
  globalThis.fetch = async () => { throw new DOMException('cancelled', 'AbortError'); };
  await sendChatMessage({ message: 'q', onEvent: e => events.push(e) });
  assert.deepEqual(events, []);
});
test('request preserves empty fork, omits undefined, sends scope cookie', async () => {
  const requests = [];
  globalThis.fetch = async (_url, init) => { requests.push(init); return new Response(frame({ type: 'done' })); };
  for (const forkFromTurnId of [undefined, '', 'turn-1']) await sendChatMessage({ message: 'q', conversationId: 'conv-1', forkFromTurnId, onEvent() {} });
  assert.deepEqual(requests.map(r => JSON.parse(r.body)), [
    { message: 'q', conversation_id: 'conv-1' },
    { message: 'q', conversation_id: 'conv-1', fork_from_turn_id: '' },
    { message: 'q', conversation_id: 'conv-1', fork_from_turn_id: 'turn-1' },
  ]);
  assert.ok(requests.every(r => r.credentials === 'include'));
});
