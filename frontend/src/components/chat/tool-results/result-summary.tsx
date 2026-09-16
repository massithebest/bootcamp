import { DataTable, Tag } from "../primitives";
import {
  asResultColumns,
  asResultSummary,
  asRows,
  asStrings,
  num,
  type ResultColumnSummary,
} from "./shared";

const ROLE_LABEL: Record<string, string> = {
  category: "범주",
  measure: "수치",
  time: "시간",
};

function formatStat(v: ResultColumnSummary["min"] | ResultColumnSummary["mean"]): string {
  if (v === null) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  return v;
}

/**
 * 대용량 조회 결과(`type: "large_result"`, plan/260915-result-store-plan.md) 요약 카드.
 * 원본 행 대신 표본 몇 행 + 컬럼별 기초 통계만 보여준다.
 * 이 카드에는 페이지 이동을 두지 않으며 독립 대화형 표는 `prepare_table`이 제공한다.
 */
export function ResultSummaryCard({ data }: { data: Record<string, unknown> }) {
  const rowCount = num(data.row_count);
  const columns = asResultColumns(data.columns);
  const sampleRows = asRows(data.sample_rows);
  const summary = asResultSummary(data.summary);
  const columnNames = columns.map((c) => c.name);

  return (
    <div className="flex flex-col gap-2 rounded border border-line bg-surface-2/50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-ui text-ink-2">
          전체 <span className="font-mono tabular-nums text-ink">{rowCount ?? "?"}</span>행
        </p>
        <Tag>샘플 {sampleRows.length}행</Tag>
      </div>

      {sampleRows.length > 0 && (
        <DataTable
          columns={columnNames.length > 0 ? columnNames : asStrings(data.columns)}
          rows={sampleRows}
        />
      )}

      {columns.length > 0 && (
        <dl className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
          {columns.map((col) => {
            const stat = summary[col.name];
            return (
              <div key={col.name} className="flex flex-col gap-0.5">
                <dt className="flex items-center gap-1.5 text-2xs text-ink-3">
                  <span className="font-mono text-ink-2">{col.name}</span>
                  {col.role && <Tag>{ROLE_LABEL[col.role] ?? col.role}</Tag>}
                </dt>
                {stat && (
                  <dd className="font-mono text-2xs tabular-nums text-ink-2">
                    min {formatStat(stat.min)} · max {formatStat(stat.max)} · 평균{" "}
                    {formatStat(stat.mean)}
                    {stat.nullCount !== null && stat.nullCount > 0 && (
                      <> · null {stat.nullCount}</>
                    )}
                  </dd>
                )}
              </div>
            );
          })}
        </dl>
      )}
    </div>
  );
}
