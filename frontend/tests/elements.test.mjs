import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let server, AgentPlan, TooltipIconButton, TooltipProvider, RetrievalChunks, DataTable, MarkdownTableBody;
let VisualizationToolUI, TableToolUI, ToolResultCard, productionPlanningToolkit;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  ({ RetrievalChunks } = await server.ssrLoadModule('/src/components/assistant-ui/elements/retrieval-chunks.tsx'));
  ({ AgentPlan } = await server.ssrLoadModule('/src/components/assistant-ui/elements/agent-plan.tsx'));
  ({ TooltipIconButton } = await server.ssrLoadModule('/src/components/assistant-ui/elements/tooltip-icon-button.tsx'));
  ({ TooltipProvider } = await server.ssrLoadModule('/src/components/ui/tooltip.tsx'));
  ({ DataTable } = await server.ssrLoadModule('/src/components/chat/primitives.tsx'));
  ({ MarkdownTableBody } = await server.ssrLoadModule('/src/components/assistant-ui/elements/markdown-text.tsx'));
  ({ ToolResultCard } = await server.ssrLoadModule('/src/components/chat/tool-result-card.tsx'));
  ({ VisualizationToolUI } = await server.ssrLoadModule('/src/components/chat/tool-results/visualization-tool-ui.tsx'));
  ({ TableToolUI } = await server.ssrLoadModule('/src/components/chat/tool-results/table-tool-ui.tsx'));
  ({ productionPlanningToolkit } = await server.ssrLoadModule('/src/components/chat/toolkit.tsx'));
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

test('table tool is a standalone render-only backend tool', () => {
  const tool = productionPlanningToolkit.prepare_table;
  assert.equal(tool.type, 'backend');
  assert.equal(tool.display, 'standalone');
  assert.equal(tool.render, TableToolUI);
  assert.equal(tool.execute, undefined);
});

test('table tool UI covers running, errors and interactive result controls', () => {
  const render = (props) => renderToStaticMarkup(createElement(TableToolUI, props));
  assert.match(render({ status: { type: 'running' } }), /표를 준비하고 있습니다/);
  assert.match(render({
    status: { type: 'complete' },
    result: { data: { status: 'error', message: '컬럼이 없습니다.' } },
  }), /컬럼이 없습니다/);

  const html = render({
    status: { type: 'complete' },
    result: { data: {
      status: 'ok',
      result_id: 'd'.repeat(32),
      title: '제품별 WIP',
      columns: ['part', 'qty'],
      rows: [['A', 10], ['B', 20]],
      row_count: 2,
      displayed_count: 2,
      source_truncated: false,
    } },
  });
  assert.match(html, /제품별 WIP/);
  assert.match(html, /표 내용 검색/);
  assert.match(html, /part 열 정렬/);
  assert.match(html, /페이지당 행/);
  assert.match(html, /다음 페이지/);
});

test('table tool UI rejects malformed or oversized result payloads', () => {
  const rows = Array.from({ length: 101 }, (_, index) => [index]);
  const html = renderToStaticMarkup(createElement(TableToolUI, {
    status: { type: 'complete' },
    result: { data: {
      status: 'ok', result_id: 'e'.repeat(32), title: null,
      columns: ['id'], rows, row_count: 101, displayed_count: 101,
      source_truncated: false,
    } },
  }));
  assert.match(html, /유효한 표 결과를 받지 못했습니다/);
});

test('visualization tool is a standalone render-only backend tool', () => {
  const tool = productionPlanningToolkit.prepare_visualization;
  assert.equal(tool.type, 'backend');
  assert.equal(tool.display, 'standalone');
  assert.equal(tool.render, VisualizationToolUI);
  assert.equal(tool.execute, undefined);
});

test('visualization tool UI covers running, safe error and validated result states', () => {
  const render = (props) => renderToStaticMarkup(createElement(VisualizationToolUI, props));

  assert.match(render({ status: { type: 'running' } }), /차트를 준비하고 있습니다/);
  assert.match(render({
    status: { type: 'complete' },
    result: { data: { status: 'error', message: '표시 한도를 초과했습니다.' } },
  }), /표시 한도를 초과했습니다/);
  assert.match(render({
    status: { type: 'complete' },
    result: { data: { status: 'ok', visualization_id: 'a'.repeat(32) } },
  }), /aria-label="차트를 불러오는 중"/);
  assert.match(render({
    status: { type: 'complete' },
    result: { data: { status: 'ok', visualization_id: 'invalid' } },
  }), /유효한 차트 결과를 받지 못했습니다/);
});


test('repeated table results have distinct page size labels', () => {
  const props = {
    status: { type: 'complete' },
    result: { data: {
      status: 'ok', result_id: 'd'.repeat(32), title: null,
      columns: ['id'], rows: [[1]], row_count: 1, displayed_count: 1,
      source_truncated: false,
    } },
  };
  const html = renderToStaticMarkup(createElement('div', null,
    createElement(TableToolUI, props), createElement(TableToolUI, props),
  ));
  const ids = [...html.matchAll(/<select id="([^"]+)"/g)].map(match => match[1]);
  const labels = [...html.matchAll(/<label for="([^"]+)"/g)].map(match => match[1]);
  assert.equal(ids.length, 2);
  assert.equal(new Set(ids).size, 2);
  assert.deepEqual(labels, ids);
});


test('a tool without a result is not marked complete after cancellation or failure', () => {
  const html = renderToStaticMarkup(createElement(ToolResultCard, {
    toolName: 'execute_sql', args: {}, running: false, messageRunning: false,
  }));
  assert.match(html, /미완료/);
  assert.doesNotMatch(html, />완료</);
});
