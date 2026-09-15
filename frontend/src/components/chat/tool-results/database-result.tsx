import { DataTable, Disclosure } from "../primitives";
import { ResultSummaryCard } from "./result-summary";
import { asRecord, asRows, asStrings, isLargeResult, str } from "./shared";

/**
 * DB 조회 결과 → 표 + 실행 SQL 펼쳐보기.
 *
 * Backend `execute_sql` 은 컬럼·행을 `table` 아래에 담는다
 * (`{ table: { columns, rows }, row_count }`). 초기 더미가 쓰던
 * 최상위 `columns`/`rows` 형태도 함께 받아준다.
 *
 * `type: "large_result"`(100행 초과, plan/260915-result-store-plan.md)면 전체 행 대신
 * `sample_rows`/`summary` 요약 카드를 렌더한다 — 페이지네이션은 두지 않는다,
 * 후속 조회는 대화로 처리된다(설계 §7·§9).
 */
export function DatabaseResult({ data }: { data: Record<string, unknown> }) {
  const sql = str(data.sql);
  const note = str(data.note);

  const table = asRecord(data.table);
  const rows = asRows(table.rows ?? data.rows);
  const declaredColumns = asStrings(table.columns ?? data.columns);
  // `get_result_page` 는 컬럼명 없이 `rows` 만 반환한다(백엔드 tools/result_tool.py) —
  // 그런 경우 인덱스를 헤더로 써서 같은 표 컴포넌트를 재사용한다.
  const columns =
    declaredColumns.length > 0
      ? declaredColumns
      : rows.length > 0
        ? rows[0].map((_, i) => String(i))
        : [];

  const summary = isLargeResult(data) || (
    typeof data.result_id === "string" && data.summary !== null &&
    typeof data.summary === "object" && !Array.isArray(data.summary)
  );
  if (!summary && (columns.length === 0 || rows.length === 0)) return null;

  return (
    <div className="flex flex-col gap-2">
      {summary ? <ResultSummaryCard data={data} /> : <DataTable columns={columns} rows={rows} />}
      {note && <p className="font-mono text-2xs text-ink-3">{note}</p>}
      {sql && (
        <Disclosure summary="실행된 SQL" dense>
          <pre className="thin-scroll mt-1 overflow-x-auto rounded bg-[#1c2530] px-3 py-2.5 font-mono text-data leading-relaxed text-[#d7dce4]">
            {sql}
          </pre>
        </Disclosure>
      )}
    </div>
  );
}
