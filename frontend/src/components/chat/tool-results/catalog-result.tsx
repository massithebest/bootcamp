/**
 * 참조한 지식(카탈로그·KPI) 조회 결과.
 *
 * Backend `tools/knowledge_tool.py` payload:
 *   { kind: "catalog", catalog_type: "table" | "kpi" | "table_list" | "kpi_list",
 *     verified?: boolean, data: {...} }
 *
 * RAG 검색 결과(`knowledge-result.tsx`)와는 다른 종류다 — 이쪽은 YAML 로 관리하는
 * 구조화 지식이고, 분석 한 번에 4~6회 호출되므로 요약 위주로 얕게 보여준다.
 */

import { DataTable, Disclosure } from "../primitives";
import { asRecord, asRecords, asStrings, str } from "./shared";

import { catalogTypeOf, type CatalogType } from "./catalog-data";

export function CatalogResult({ data }: { data: Record<string, unknown> }) {
  const type = catalogTypeOf(data.catalog_type);
  if (!type) return null;

  if (type === "table") return <TableDetail data={data.data} />;
  if (type === "kpi") return <KpiDetail data={data.data} />;
  if (type === "recipe") return <RecipeDetail data={data.data} />;
  return <NameList type={type} data={data.data} />;
}

/** 테이블 상세 → 컬럼 목록만. 조인·주의사항은 에이전트용이라 접어 둔다. */
function TableDetail({ data }: { data: unknown }) {
  const table = asRecord(data);
  const columns = asRecords(table.columns);
  const description = str(table.description);

  if (columns.length === 0) return description ? <Note text={description} /> : null;

  return (
    <div className="flex flex-col gap-2">
      {description && <Note text={description} />}
      <DataTable
        columns={["컬럼", "타입", "설명"]}
        rows={columns.map((column) => [
          str(column.name) ?? "",
          str(column.type) ?? "",
          str(column.desc) ?? "",
        ])}
      />
    </div>
  );
}

/** KPI 상세 → 정의·공식·판정 기준. */
function KpiDetail({ data }: { data: unknown }) {
  const kpi = asRecord(data);
  const rows: [string, string][] = [
    ["정의", str(kpi.definition) ?? ""],
    ["공식", str(kpi.formula) ?? ""],
    ["판정 기준", str(kpi.shortfall_rule) ?? ""],
  ].filter((row): row is [string, string] => row[1].length > 0);

  if (rows.length === 0) return null;

  return (
    <dl className="flex flex-col gap-1.5">
      {rows.map(([term, value]) => (
        <div key={term} className="flex gap-2.5 text-ui">
          <dt className="w-16 shrink-0 text-2xs text-ink-3">{term}</dt>
          <dd className="min-w-0 flex-1 break-words font-mono text-data leading-relaxed text-ink-2">
            {value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** 목록 → 이름 · 설명 한 줄씩. */
function NameList({ type, data }: { type: CatalogType; data: unknown }) {
  const items = asRecords(data);
  if (items.length === 0) return <Note text="해당하는 항목이 없습니다." />;

  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((item, i) => {
        const name =
          type === "table_list" ? str(item.table) : str(item.name) ?? str(item.kpi_id);
        const description =
          (type === "table_list" || type === "recipe_list")
            ? str(item.description)
            : asStrings(item.aliases).join(" · ");
        return (
          <li key={name ?? i} className="flex flex-wrap items-baseline gap-x-2 text-ui">
            <span className="font-mono text-data text-ink">{name}</span>
            {description && (
              <span className="min-w-0 text-2xs text-ink-3">{description}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function Note({ text }: { text: string }) {
  return <p className="text-2xs leading-snug text-ink-3">{text}</p>;
}

function RecipeDetail({ data }: { data: unknown }) {
  const recipe = asRecord(data);
  const sql = str(recipe.cte_sql);
  const description = str(recipe.description);
  return (
    <div className="flex flex-col gap-2">
      {str(recipe.name) && <p className="font-medium text-ink">{str(recipe.name)}</p>}
      {description && <Note text={description} />}
      {asStrings(recipe.output_grain).length > 0 && <Note text={`결과 단위: ${asStrings(recipe.output_grain).join(" · ")}`} />}
      {sql && <Disclosure summary="CTE SQL" dense><pre className="thin-scroll overflow-x-auto font-mono text-data text-ink-2">{sql}</pre></Disclosure>}
    </div>
  );
}
