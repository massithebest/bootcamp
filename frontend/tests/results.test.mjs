import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
let server;
const modules = {};
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  for (const name of ['simulation', 'database', 'knowledge', 'catalog']) modules[name] = await server.ssrLoadModule(`/src/components/chat/tool-results/${name}-result.tsx`);
});
after(async () => { await server.close(); });
const render = (name, data) => renderToStaticMarkup(createElement(modules[name][`${name[0].toUpperCase() + name.slice(1)}Result`], { data }));
test('numeric simulation KPIs include zero', () => {
  const html = render('simulation', { kpis: [{ label: 'Part', value: 10 }, { label: '미연결', value: 0 }] });
  assert.match(html, />10</); assert.match(html, />0</);
});
test('preview summary displays row count and column statistics', () => {
  const html = render('database', { status: 'ok', result_id: 'fixture', row_count: 250, columns: [{ name: 'qty', dtype: 'int64', role: 'measure' }], sample_rows: [{ qty: 20 }], statistics: { qty: { min: 1, max: 40, mean: 20, null_count: 0 } } });
  assert.match(html, /250/); assert.match(html, /40/); assert.match(html, /qty/);
});
test('simulation discovery renders available type', () => {
  const html = render('simulation', { simulations: [{ type: '입력검증', name: '입력검증', when_to_use: '관계 검증' }] });
  assert.match(html, /입력검증/);
});
test('mock and existing RAG document formats are both visible', () => {
  const html = render('knowledge', { documents: [{ title: 'mock', content: '문서 본문', score: 0.82 }, { title: 'existing', snippet: '발췌', relevance: 0.9 }] });
  assert.match(html, /문서 본문/); assert.match(html, /82/); assert.match(html, /발췌/); assert.match(html, /90/);
});
test('recipe details and list remain visible', () => {
  assert.match(render('catalog', { catalog_type: 'recipe', data: { name: 'WIP recipe', description: '제품별 집계', cte_sql: 'SELECT part FROM wip' } }), /제품별 집계/);
  assert.match(render('catalog', { catalog_type: 'recipe_list', data: [{ name: 'WIP recipe', description: '제품별 집계' }] }), /WIP recipe/);
});
test('inline table and preview summary retain source values', () => {
  assert.match(render('database', { table: { columns: ['part', 'qty'], rows: [['part_1', 12]] } }), /part_1/);
  assert.match(render('database', { status: 'ok', result_id: 'fixture', row_count: 500, columns: [{ name: 'qty' }], sample_rows: [{ qty: 42 }], statistics: {} }), /42/);
});
test('table cells drop floating point aggregation noise', async () => {
  const { displayCell } = await server.ssrLoadModule('/src/lib/format-cell.ts');
  assert.equal(displayCell(13083.199999999999), '13083.2');
  assert.equal(displayCell(0.1 + 0.2), '0.3');
  assert.equal(displayCell(7072.3), '7072.3');
  assert.equal(displayCell(5882), '5882');
  assert.equal(displayCell(null), '—');
});
test('KPI cards group thousands and space latin units only', async () => {
  const kpis = [{ label: '초기 WIP', value: 2255, unit: 'lot' }, { label: 'Part', value: 2, unit: '개' }, { label: '달성률', value: 50.789, unit: '%' }];
  const { SimulationSummary } = await server.ssrLoadModule('/src/components/chat/generative/simulation-summary.tsx');
  const summary = renderToStaticMarkup(createElement(SimulationSummary, { scenario: 'SEG_A 입력 검증', summary: '정상', kpis }));
  const result = render('simulation', { kpis });
  for (const html of [summary, result]) {
    const text = html.replace(/<[^>]+>/g, '');
    assert.match(text, /2,255 lot/);
    assert.match(text, /2개/);
    assert.match(text, /50\.79%/);
  }
});
