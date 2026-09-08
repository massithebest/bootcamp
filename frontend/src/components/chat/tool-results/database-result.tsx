"use client";

import { DataTable, Disclosure } from "../primitives";
import { asRows, asStrings, str } from "./shared";

/** DB 조회 결과 → 표 + 실행 SQL 펼쳐보기. */
export function DatabaseResult({ data }: { data: Record<string, unknown> }) {
  const columns = asStrings(data.columns);
  const rows = asRows(data.rows);
  const sql = str(data.sql);
  const note = str(data.note);

  if (columns.length === 0 || rows.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <DataTable columns={columns} rows={rows} />
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
