import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server, AgentPlan, TooltipIconButton, TooltipProvider, RetrievalChunks, DataTable, MarkdownTableBody;
let ToolResultCard;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  ({ RetrievalChunks } = await server.ssrLoadModule('/src/components/assistant-ui/elements/retrieval-chunks.tsx'));
  ({ AgentPlan } = await server.ssrLoadModule('/src/components/assistant-ui/elements/agent-plan.tsx'));
  ({ TooltipIconButton } = await server.ssrLoadModule('/src/components/assistant-ui/elements/tooltip-icon-button.tsx'));
  ({ TooltipProvider } = await server.ssrLoadModule('/src/components/ui/tooltip.tsx'));
  ({ DataTable } = await server.ssrLoadModule('/src/components/chat/primitives.tsx'));
  ({ MarkdownTableBody } = await server.ssrLoadModule('/src/components/assistant-ui/elements/markdown-text.tsx'));
  ({ ToolResultCard } = await server.ssrLoadModule('/src/components/chat/tool-result-card.tsx'));
});
after(async () => { await server.close(); });

test('plan counts only completed steps and preserves errors and interruptions', () => {
  const html = renderToStaticMarkup(createElement(AgentPlan, { steps: [
    { id: 'done', label: '조회', status: 'completed' },
    { id: 'failed', label: '검증', status: 'error' },
    { id: 'stopped', label: '분석', status: 'stopped' },
    { id: 'pending', label: '답변', status: 'pending' },
    { id: 'unknown', label: '최종 상태 없음', status: 'unknown' },
  ] }));
  assert.match(html, /aria-valuenow="1"/);
  assert.match(html, /aria-valuemax="5"/);
  assert.match(html, />오류</);
  assert.match(html, />중단</);
  assert.match(html, />대기</);
  assert.match(html, />완료 미확인</);
});

test('tooltip actions retain native button disabled semantics', () => {
  const render = (disabled) => renderToStaticMarkup(createElement(TooltipProvider, null,
    createElement(TooltipIconButton, { tooltip: '전송', disabled }, '↑')));
  assert.match(render(true), /<button[^>]*disabled=""/);
  assert.doesNotMatch(render(false), /<button[^>]*disabled=""/);
  assert.match(render(true), /aria-label="전송"/);
});


test('retrieval shows zero but omits missing, non-finite and out-of-range relevance', () => {
  const scores = [0, 1, undefined, null, -1, 2, NaN, Infinity];
  const html = renderToStaticMarkup(createElement(RetrievalChunks, {
    query: 'route', chunks: scores.map((score, i) => ({ id: String(i), source: `source-${i}`, score, text: 'full passage' })),
  }));
  assert.equal((html.match(/role="meter"/g) ?? []).length, 2);
  assert.match(html, /관련도 0%/);
  assert.match(html, /관련도 100%/);
  assert.equal((html.match(/full passage/g) ?? []).length, scores.length);
  assert.match(renderToStaticMarkup(createElement(RetrievalChunks, { chunks: [] })), /검색된 문서가 없습니다/);
});

test('data tables render at most one hundred data rows and report omitted rows', () => {
  const rows = Array.from({ length: 102 }, (_, index) => [`row-${index + 1}`]);
  const html = renderToStaticMarkup(createElement(DataTable, { columns: ['name'], rows }));

  assert.match(html, /row-100/);
  assert.doesNotMatch(html, /row-101/);
  assert.match(html, /전체 102건 중 100건 표시/);
  assert.match(html, /2건 생략/);
});

test('markdown table bodies render at most one hundred data rows', () => {
  const rows = Array.from({ length: 102 }, (_, index) =>
    createElement('tr', { key: index }, createElement('td', null, `markdown-row-${index + 1}`)),
  );
  const html = renderToStaticMarkup(createElement('table', null,
    createElement(MarkdownTableBody, null, rows),
  ));

  assert.match(html, /markdown-row-100/);
  assert.doesNotMatch(html, /markdown-row-101/);
  assert.match(html, /전체 102건 중 100건 표시/);
});

test('a tool without a result is not marked complete after cancellation or failure', () => {
  const html = renderToStaticMarkup(createElement(ToolResultCard, {
    toolName: 'execute_sql', args: {}, running: false, messageRunning: false,
  }));
  assert.match(html, /미완료/);
  assert.doesNotMatch(html, />완료</);
});
