import { DataTable, Disclosure, StatusDot } from "../primitives";
import { ResultSummaryCard } from "./result-summary";
import { asRecord, asRecords, asRows, asStrings, isLargeResult, num, str, toneOf } from "./shared";

/** 레코드 배열(`[{line, workMonth, qty}]` 등)의 컬럼명을 첫 원소의 key 순서로 뽑는다. */
function columnsOfRecords(records: Record<string, unknown>[]): string[] {
  return records.length > 0 ? Object.keys(records[0]) : [];
}

/** 시뮬레이션 결과 → 핵심 수치 + 병목/제약 요약이 즉시 읽히도록. 표는 접어서. */
export function SimulationResult({ data }: { data: Record<string, unknown> }) {
  const scenario = str(data.scenario);
  const summary = str(data.summary);
  const kpis = asRecords(data.kpis);
  const table = asRecord(data.table);
  const tableColumns = table ? asStrings(table.columns) : [];
  const tableRows = table ? asRows(table.rows) : [];

  const results = asRecords(data.results);
  const resultColumns = columnsOfRecords(results);
  const resultRows = results.map((r) => resultColumns.map((c) => String(r[c] ?? "")));
  const large = isLargeResult(data);
  const simulations = asRecords(data.simulations);

  return (
    <div className="flex flex-col gap-3">
      {simulations.length > 0 && (
        <DataTable
          columns={["종류", "이름", "사용 시점"]}
          rows={simulations.map((s) => [str(s.type) ?? "", str(s.name) ?? "", str(s.when_to_use) ?? ""])}
        />
      )}
      {scenario && (
        <p className="font-mono text-2xs text-ink-3">{scenario}</p>
      )}

      {kpis.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          {kpis.map((kpi, i) => {
            const tone = toneOf(kpi.tone);
            return (
              <div key={i} className="flex flex-col gap-1">
                <dt className="flex items-center gap-1.5 text-2xs text-ink-3">
                  {tone !== "neutral" && <StatusDot tone={tone} />}
                  {str(kpi.label) ?? ""}
                </dt>
                <dd className="font-mono text-ui-lg font-medium tabular-nums text-ink">
                  {num(kpi.value) ?? str(kpi.value) ?? "—"}
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

      {/* 배열형 simulation 결과가 대용량(100행 초과, plan/260915-result-store-plan.md)이면
          `results` 는 sample_rows 로 축소되어 있다 — 표 대신 요약 카드로 렌더한다. */}
      {large ? (
        <ResultSummaryCard data={data} />
      ) : (
        resultColumns.length > 0 &&
        resultRows.length > 0 && <DataTable columns={resultColumns} rows={resultRows} />
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
