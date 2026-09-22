import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

let server, api, lineDiff, formatTime, blank, FieldEditor, DiffView, ChangeStateBadge, ChangeHistory, ValidationSummary, UserSwitcher;
const originalFetch = globalThis.fetch;
const storage = new Map();
before(async () => {
  // 브라우저 전역이 필요한 API 모듈용 최소 대체. 실제 저장소 접근은 없다.
  globalThis.window = { dispatchEvent: () => true, localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) } };
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  api = await server.ssrLoadModule('/src/lib/knowledge-api.ts');
  lineDiff = await server.ssrLoadModule('/src/lib/line-diff.ts');
  ({ formatTime } = await server.ssrLoadModule('/src/lib/format-time.ts'));
  blank = await server.ssrLoadModule('/src/components/knowledge/editor/blank-value.ts');
  ({ FieldEditor } = await server.ssrLoadModule('/src/components/knowledge/editor/field-editor.tsx'));
  ({ DiffView } = await server.ssrLoadModule('/src/components/knowledge/editor/diff-view.tsx'));
  ({ ChangeStateBadge } = await server.ssrLoadModule('/src/components/knowledge/editor/change-badge.tsx'));
  ({ ChangeHistory } = await server.ssrLoadModule('/src/components/knowledge/editor/change-history.tsx'));
  ({ ValidationSummary } = await server.ssrLoadModule('/src/components/knowledge/editor/validation-summary.tsx'));
  ({ UserSwitcher } = await server.ssrLoadModule('/src/components/knowledge/editor/user-switcher.tsx'));
});
after(async () => { globalThis.fetch = originalFetch; delete globalThis.window; await server.close(); });

const field = (name, widget, extra = {}) => ({ name, path: name, label: name, help: '', required: false, readonly: false, widget, ...extra });
const guideFields = [
  field('table', 'string', { label: '테이블명', help: '실제 테이블 이름', required: true, example: 'lot_status', group: '기본 정보' }),
  field('description', 'text', { label: '설명', required: true, group: '기본 정보' }),
  field('grain', 'string_list', { label: '행 단위', item_widget: 'string', required: true, group: '기본 정보' }),
  field('query_rules', 'string_list', { label: '조회 규칙', item_widget: 'text', group: '규칙·가이드' }),
  field('columns', 'record_list', { label: '컬럼', required: true, group: '구조', fields: [
    { ...field('name', 'string', { label: '컬럼명', required: true }), path: 'columns.name' },
    { ...field('type', 'string', { label: '타입', required: true }), path: 'columns.type' },
    { ...field('desc', 'string', { label: '설명' }), path: 'columns.desc' },
  ] }),
  field('params', 'map', { label: '입력 파라미터', group: '구조', value: { widget: 'object', fields: [{ ...field('required', 'boolean', { label: '필수', required: true }), path: 'params.required' }] } }),
  field('output_schema', 'json', { label: '출력 스키마', group: '구조' }),
  field('active', 'boolean', { label: '사용 여부', group: '관리 정보' }),
  field('status', 'enum', { label: '검토 상태', options: ['draft', 'verified'], readonly: true, group: '관리 정보' }),
  field('updated', 'date', { label: '수정일', readonly: true, group: '관리 정보' }),
];
const value = { table: 'wip', description: '설명', grain: ['dataset', 'lot'], query_rules: ['기간을 건다'], columns: [{ name: 'lot', type: 'varchar' }], params: { dataset: { required: true } }, output_schema: { a: 1 }, active: true, status: 'draft' };
const render = (props) => renderToStaticMarkup(createElement(FieldEditor, { fields: guideFields, value, onChange: () => {}, errors: {}, ...props }));

test('line diff marks additions and deletions and folds unchanged runs', () => {
  const rows = lineDiff.diffLines('a\nb\nc\nd\ne\nf\ng\nh\n', 'a\nb\nc\nX\ne\nf\ng\nh\ni\n');
  assert.deepEqual(rows.filter(r => r.kind !== 'same').map(r => `${r.kind}:${r.text}`), ['del:d', 'add:X', 'add:i']);
  assert.equal(lineDiff.hasChanges(lineDiff.diffLines('same\n', 'same\n')), false);
  assert.deepEqual(lineDiff.diffLines('', 'x\ny').map(r => r.kind), ['add', 'add']);
  const long = Array.from({ length: 40 }, (_, i) => `line${i}`).join('\n');
  const chunks = lineDiff.collapseUnchanged(lineDiff.diffLines(long, long.replace('line20', 'changed')));
  assert.ok(chunks.some(c => c.kind === 'gap' && c.count > 10), 'unchanged stretch should collapse');
  assert.ok(chunks.length < 20);
});

test('blank values include only required fields so optional strings never become empty text', () => {
  assert.deepEqual(blank.blankRecord(guideFields.find(f => f.name === 'columns').fields), { name: '', type: '' });
  assert.equal(blank.blankValue({ widget: 'enum', options: ['sql', 'simulation'] }), 'sql');
  assert.deepEqual(blank.blankValue({ widget: 'map' }), {});
});

test('field editor renders guide labels, help, required markers, groups and locked keys', () => {
  const html = render({ locked: new Set(['table']) });
  for (const text of ['테이블명', '실제 테이블 이름', '기본 정보', '규칙·가이드', '관리 정보', '컬럼 1', '컬럼 추가', '행 단위 추가', '조회 규칙 1']) assert.match(html, new RegExp(text));
  assert.match(html, /for="field-table"/);
  assert.match(html, /id="field-table" readonly=""/, 'key field should be locked');
  assert.match(html, /placeholder="lot_status"/);
  assert.match(html, /<textarea[^>]*aria-label="조회 규칙 1"/, 'text list items use multi-line input');
  assert.match(html, /필수/);
  assert.match(html, /승인할 때 기록됩니다/, 'empty date is explained, not blank');
  assert.doesNotMatch(html, /검토 상태[^]*<select/, 'readonly enum is text, not an editable select');
});

test('field editor shows inline errors bound to exact paths and keeps read-only forms free of edit buttons', () => {
  const html = render({ errors: { 'columns[0].type': ['타입은(는) 필수입니다.'], description: ['설명은(는) 필수입니다.'] } });
  assert.match(html, /타입은\(는\) 필수입니다\./);
  assert.match(html, /aria-invalid="true"/);
  const locked = render({ readOnly: true });
  assert.doesNotMatch(locked, /컬럼 추가|행 단위 추가|삭제/);
});

test('diff view exposes changes without relying on color alone', () => {
  const html = renderToStaticMarkup(createElement(DiffView, { before: 'a: 1\nb: 2\n', after: 'a: 1\nb: 3\n' }));
  assert.match(html, /1줄 추가 · 1줄 삭제/);
  assert.match(html, /sr-only[^>]*>추가: /); assert.match(html, /sr-only[^>]*>삭제: /);
  assert.match(html, />\+</); assert.match(html, />−</);
  assert.match(renderToStaticMarkup(createElement(DiffView, { before: 'a\n', after: 'a\n' })), /달라진 내용이 없습니다/);
  assert.match(renderToStaticMarkup(createElement(DiffView, { before: '', after: 'a\n' })), /새 지식입니다/);
});

test('status, validation and history render text alongside color', () => {
  for (const [state, label] of [['draft', '초안'], ['submitted', '검토 대기'], ['approved', '승인됨'], ['rejected', '반려됨'], ['withdrawn', '철회됨']]) assert.match(renderToStaticMarkup(createElement(ChangeStateBadge, { state })), new RegExp(label));
  assert.match(renderToStaticMarkup(createElement(ValidationSummary, { errors: [], ok: true, checking: false })), /검증을 통과했습니다/);
  const failing = renderToStaticMarkup(createElement(ValidationSummary, { errors: [{ path: 'columns[0].name', line: null, message: '필수입니다' }, { path: '', line: 3, message: 'YAML 문법 오류' }], ok: false, checking: false }));
  assert.match(failing, /확인이 필요한 항목 2개/); assert.match(failing, /3행/);
  assert.match(renderToStaticMarkup(createElement(ValidationSummary, { errors: [], ok: false, checking: true })), /검증 중/);
  const history = renderToStaticMarkup(createElement(ChangeHistory, { items: [{ revision: 3, action: 'approve', actor_id: 'a', actor_name: '관리자', note: '근거 확인', self_approved: true, at: '2026-09-21T12:50:15.242501+00:00' }] }));
  assert.match(history, /승인/); assert.match(history, /작성자 본인 승인/); assert.match(history, /근거 확인/);
  assert.doesNotMatch(history, /242501|\+00:00/, 'timestamps are formatted, not raw ISO');
  assert.equal(formatTime('not-a-date'), 'not-a-date');
});

test('user switcher is only offered for the stub and says it is not real authentication', () => {
  const me = { id: 'user', name: '사용자', permissions: ['knowledge:write'], mode: 'stub', knowledge_management: true, allow_self_approval: false, stub_users: [{ id: 'user', name: '사용자' }, { id: 'admin', name: '관리자' }] };
  const stub = renderToStaticMarkup(createElement(UserSwitcher, { me }));
  assert.match(stub, /aria-label="작업 사용자"/); assert.match(stub, /보안 인증이 아닙니다/); assert.match(stub, /작성/);
  const real = renderToStaticMarkup(createElement(UserSwitcher, { me: { ...me, mode: 'authenticated', permissions: ['knowledge:write', 'knowledge:approve'] } }));
  assert.doesNotMatch(real, /<select/); assert.match(real, /작성·승인/);
});

const change = { id: 'c1', kind: 'table', key: 'wip', is_new: false, state: 'draft', revision: 1, author: { id: 'user', name: '사용자' }, created_at: 't', updated_at: 't', yaml: 'a: 1\n', data: { a: 1 }, current_yaml: '', history: [] };
test('change API sends the stub user, validates responses and maps errors without server text', async () => {
  storage.set('pp.knowledge.stub-user', 'admin');
  const seen = [];
  globalThis.fetch = async (url, init) => { seen.push({ url: String(url), init }); return Response.json(change); };
  assert.equal((await api.fetchChange('c1')).key, 'wip');
  assert.equal(seen[0].init.headers['X-User-Id'], 'admin');
  await api.updateChange('c1', 1, { yaml: 'a: 1\n' });
  assert.equal(seen[1].init.method, 'PUT'); assert.deepEqual(JSON.parse(seen[1].init.body), { expected_revision: 1, yaml: 'a: 1\n' });
  await api.actOnChange('c1', 'approve', 2, '근거');
  assert.match(seen[2].url, /\/changes\/c1\/approve$/); assert.deepEqual(JSON.parse(seen[2].init.body), { expected_revision: 2, note: '근거' });
  await api.createChange('glossary', { data: { term: 'x' } });
  assert.deepEqual(JSON.parse(seen[3].init.body), { kind: 'glossary', data: { term: 'x' } });

  for (const [status, pattern] of [[403, /권한/], [409, /다른 변경/], [422, /필수 입력/]]) {
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: `secret-${status}` }), { status });
    await assert.rejects(api.actOnChange('c1', 'approve', 1, 'n'), error => pattern.test(error.message) && !/secret/.test(error.message));
  }
  globalThis.fetch = async () => Response.json({ ...change, state: 'bogus' });
  await assert.rejects(api.fetchChange('c1'), /응답 형식/);
  storage.delete('pp.knowledge.stub-user');
});

test('validation, guide and me responses are checked before use', async () => {
  globalThis.fetch = async () => Response.json({ ok: true, parsed: true, yaml: 'a: 1\n', data: {}, key: 'a', errors: [] });
  assert.equal((await api.validateKnowledge('table', { data: {} })).ok, true);
  globalThis.fetch = async () => Response.json({ ok: 'yes' });
  await assert.rejects(api.validateKnowledge('table', { yaml: 'a' }), /응답 형식/);
  globalThis.fetch = async () => Response.json([]);
  await assert.rejects(api.fetchMe(), /응답 형식/, 'an unexpected me payload must not grant write access');
  globalThis.fetch = async () => Response.json({ kind: 'table', key_field: 'table', fields: [{ name: 'x' }], template: {}, immutable: [] });
  await assert.rejects(api.fetchKnowledgeGuide('table'), /응답 형식/);
  let requested;
  globalThis.fetch = async url => { requested = String(url); return Response.json([]); };
  await api.fetchChanges({ state: 'submitted', mine: true });
  assert.match(requested, /\/changes\?state=submitted&mine=true$/);
});
