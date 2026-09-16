import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
let server, api, KnowledgeResult, StructuredDetail, SkillMarkdown;
const originalFetch = globalThis.fetch;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  api = await server.ssrLoadModule('/src/lib/knowledge-api.ts');
  ({ KnowledgeResult } = await server.ssrLoadModule('/src/components/chat/tool-results/knowledge-result.tsx'));
  ({ StructuredDetail } = await server.ssrLoadModule('/src/components/knowledge/structured-detail.tsx'));
  ({ SkillMarkdown } = await server.ssrLoadModule('/src/components/chat/skill-markdown.tsx'));
});
after(async () => { globalThis.fetch = originalFetch; await server.close(); });
const version = { version: 1, title: '제목', content: '본문', category: '정책', tags: [], owner: '담당', source: '근거', status: 'verified', created_at: '2026-09-16', reviewer: '검토자', review_note: '확인', reviewed_at: '2026-09-16' };
const document = { id: 'a', revision: 2, active_version: 1, archived: false, versions: [version], history: [] };
test('document response rejects invalid publication pointers and version fields', () => {
  assert.ok(api.isKnowledgeDocument(document));
  for (const malformed of [{ ...document, active_version: 99 }, { ...document, versions: [{ ...version, status: 'draft' }] }, { ...document, revision: -1 }, { ...document, versions: [] }, { ...document, versions: [{ ...version, tags: [2] }] }]) assert.equal(api.isKnowledgeDocument(malformed), false);
});
test('API errors do not expose server text and search includes full query', async () => {
  globalThis.fetch = async (url) => {
    assert.match(String(url), /entries\?q=/);
    return new Response('internal /private/path', { status: 503 });
  };
  await assert.rejects(api.fetchKnowledgeEntries(undefined, '본문검색'), /처리하지 못했습니다/);
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'secret' }), { status: 409 });
  await assert.rejects(api.fetchDocument('a'), /다른 변경/);
  globalThis.fetch = async () => new Response(JSON.stringify({ ...document, versions: [] }));
  await assert.rejects(api.fetchDocument('a'), /응답 형식/);
});
test('citations display exact version and source without inventing relevance', () => {
  const html = renderToStaticMarkup(createElement(KnowledgeResult, { data: { documents: [{ document_id: 'a', version: 1, title: '<script>unsafe</script>', snippet: '<img onerror=alert(1)>', source: '검토 회의', verified: true }] } }));
  assert.match(html, /v1 원문 보기/); assert.match(html, /검토 회의/); assert.match(html, /검토 완료/);
  assert.doesNotMatch(html, /<script>|<img onerror|NaN|%/);
});
test('structured knowledge renders consistent labels, chips, columns, and empty values without raw JSON', () => {
  const html = renderToStaticMarkup(createElement(StructuredDetail, { data: {
    time_column: null,
    tags: ['SMT2020', '설비'],
    columns: [{ name: 'dataset', type: 'varchar', desc: 'benchmark 구분', ref: null }],
    caveats: ['dataset을 먼저 확정한다'],
  } }));
  assert.match(html, /시간 컬럼/);
  assert.match(html, /태그/);
  assert.match(html, /컬럼/);
  assert.match(html, /dataset/);
  assert.match(html, /benchmark 구분/);
  assert.match(html, /없음/);
  assert.doesNotMatch(html, /&quot;(name|type|desc|ref)&quot;|>null</);
});
test('skill markdown renders readable nested headings and lists instead of raw source', () => {
  const html = renderToStaticMarkup(createElement(SkillMarkdown, { content: '# 분석 절차\n\n## 단계\n\n1. **확인**: `list_kpis` 실행\n2. 원인 검증' }));
  assert.match(html, /<h4[^>]*>분석 절차<\/h4>/);
  assert.match(html, /<h5[^>]*>단계<\/h5>/);
  assert.match(html, /<ol/);
  assert.match(html, /<strong[^>]*>확인<\/strong>/);
  assert.doesNotMatch(html, /# 분석 절차|\*\*확인\*\*/);
});
