import { DataTable, Disclosure } from "../primitives";
import { ResultSummaryCard } from "./result-summary";
import { asRecord, asRows, asStrings, isPreviewResult, str } from "./shared";

/**
 * DB 조회 결과 → 표 + 실행 SQL 펼쳐보기.
 *
 * Backend `execute_sql` 은 컬럼·행을 `table` 아래에 담는다
 * (`{ table: { columns, rows }, row_count }`). 초기 더미가 쓰던
 * 최상위 `columns`/`rows` 형태도 함께 받아준다.
 *
 * preview(bounded `sample_rows`/`statistics`)면 전체 행 대신 요약 카드를 렌더한다.
 * 이 실행 상세 카드에는 페이지 이동을 넣지 않고, 독립적인 검색·정렬·페이지 이동
 * 표는 `present_table` Tool UI가 맡는다.
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

  const summary = isPreviewResult(data);
  const empty = data.row_count === 0 && rows.length === 0;

  return (
    <div className="flex flex-col gap-2">
      {empty ? <p className="text-ui text-ink-2">조회 결과 0건입니다. 조건에 맞는 데이터가 없습니다.</p>
        : summary ? <ResultSummaryCard data={data} />
          : columns.length && rows.length ? <DataTable columns={columns} rows={rows} />
            : <p className="text-ui text-ink-2">표시할 조회 데이터가 전달되지 않았습니다. 실행 상태와 조건을 확인하세요.</p>}
      {note && <p className="font-mono text-2xs text-ink-2">{note}</p>}
      {sql && (
        <Disclosure summary="실행된 SQL" dense>
          <pre tabIndex={0} aria-label="실행된 SQL 전체 내용" className="thin-scroll mt-1 max-h-96 overflow-auto rounded bg-[#1c2530] px-3 py-2.5 font-mono text-data leading-relaxed text-[#d7dce4]">
            {sql}
          </pre>
        </Disclosure>
      )}
    </div>
  );
}
