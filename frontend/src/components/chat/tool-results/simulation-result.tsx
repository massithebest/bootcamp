import { DataTable, Disclosure, StatusDot, type Tone } from "../primitives";
import { asRecords, asRows, asStrings, str, toneOf } from "./shared";

/** 시뮬레이션 결과 → 핵심 수치 + 병목/제약 요약이 즉시 읽히도록. 표는 접어서. */
export function SimulationResult({ data }: { data: Record<string, unknown> }) {
  const scenario = str(data.scenario);
  const summary = str(data.summary);
  const kpis = asRecords(data.kpis);
  const table = data.table as Record<string, unknown> | undefined;
  const tableColumns = table ? asStrings(table.columns) : [];
  const tableRows = table ? asRows(table.rows) : [];

  return (
    <div className="flex flex-col gap-3">
      {scenario && (
        <p className="font-mono text-2xs text-ink-3">{scenario}</p>
      )}

      {kpis.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          {kpis.map((kpi, i) => {
            const tone = toneOf(kpi.tone) as Tone;
            return (
              <div key={i} className="flex flex-col gap-1">
                <dt className="flex items-center gap-1.5 text-2xs text-ink-3">
                  {tone !== "neutral" && <StatusDot tone={tone} />}
                  {str(kpi.label) ?? ""}
                </dt>
                <dd className="font-mono text-ui-lg font-medium tabular-nums text-ink">
                  {str(kpi.value) ?? "—"}
                  {str(kpi.unit) && (
                    <span className="ml-0.5 text-2xs font-normal text-ink-3">
                      {str(kpi.unit)}
                    </span>
                  )}
                </dd>
              </div>
            );
          })}
        </dl>
      )}

      {summary && (
        <p className="text-ui leading-relaxed text-ink-2">{summary}</p>
      )}

      {tableColumns.length > 0 && tableRows.length > 0 && (
        <Disclosure summary={`상세 (${tableRows.length}행)`} dense>
          <div className="mt-1">
            <DataTable columns={tableColumns} rows={tableRows} />
          </div>
        </Disclosure>
      )}
    </div>
  );
}
