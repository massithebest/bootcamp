import { DataTable, Disclosure } from "../primitives";
import { asRows, asStrings, str } from "./shared";

/**
 * DB 조회 결과 → 표 + 실행 SQL 펼쳐보기.
 *
 * Backend `execute_sql` 은 컬럼·행을 `table` 아래에 담는다
 * (`{ table: { columns, rows }, row_count, truncated }`). 초기 더미가 쓰던
 * 최상위 `columns`/`rows` 형태도 함께 받아준다.
 */
export function DatabaseResult({ data }: { data: Record<string, unknown> }) {
  const table = (data.table ?? {}) as Record<string, unknown>;
  const columns = asStrings(table.columns ?? data.columns);
  const rows = asRows(table.rows ?? data.rows);
  const sql = str(data.sql);
  const note = str(data.note);
  const truncated = data.truncated === true;

  if (columns.length === 0 || rows.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <DataTable columns={columns} rows={rows} />
      {truncated && (
        <p className="text-2xs text-warn-ink">
          결과가 많아 {rows.length}행까지만 표시했습니다.
        </p>
      )}
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
