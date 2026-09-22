/** tool_result data(Record<string, unknown>) 안전 파싱 helper. */

export function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

export function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function asRecord(v: unknown): Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v)
    ? v as Record<string, unknown>
    : {};
}

export function asStrings(v: unknown): string[] {
  return Array.isArray(v) ? v.map((x) => String(x)) : [];
}

export function asRows(v: unknown): string[][] {
  if (!Array.isArray(v)) return [];
  return v
    .filter((row): row is unknown[] => Array.isArray(row))
    .map((row) => row.map((cell) => String(cell)));
}

/** 조회 preview의 `sample_rows`는 객체 배열이다. */
export function asSampleRows(v: unknown, columnNames: string[]): string[][] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((row): string[][] => {
    if (typeof row === "object" && row !== null && !Array.isArray(row)) {
      const record = row as Record<string, unknown>;
      const names = columnNames.length > 0 ? columnNames : Object.keys(record);
      return [names.map((name) => (record[name] == null ? "—" : String(record[name])))];
    }
    return [];
  });
}

export function asRecords(v: unknown): Record<string, unknown>[] {
  if (!Array.isArray(v)) return [];
  return v.filter(
    (x): x is Record<string, unknown> =>
      typeof x === "object" && x !== null && !Array.isArray(x),
  );
}

export type ResultTone = "neutral" | "ok" | "warn" | "block";

export function toneOf(v: unknown): ResultTone {
  return v === "ok" || v === "warn" || v === "block" ? v : "neutral";
}

/**
 * `execute_sql`·`run_simulation` 결과는 전체 행 대신 bounded preview
 * (`sample_rows`, `statistics` …)만 담는다. `database-result.tsx`/
 * `simulation-result.tsx` 양쪽에서 같은 판별 로직을 쓴다.
 */
export function isPreviewResult(data: Record<string, unknown>): boolean {
  return (
    typeof data.result_id === "string" &&
    Array.isArray(data.sample_rows) &&
    typeof data.statistics === "object" &&
    data.statistics !== null &&
    !Array.isArray(data.statistics)
  );
}

export interface ResultColumn {
  name: string;
  dtype: string;
  role: "category" | "measure" | "time" | null;
}

export function asResultColumns(v: unknown): ResultColumn[] {
  if (!Array.isArray(v)) return [];
  return v
    .filter((x): x is Record<string, unknown> => typeof x === "object" && x !== null)
    .map(
      (c): ResultColumn => ({
        name: str(c.name) ?? "",
        dtype: str(c.dtype) ?? "",
        role:
          c.role === "category"
            ? "category"
            : c.role === "measure"
              ? "measure"
              : c.role === "time"
                ? "time"
                : null,
      }),
    )
    .filter((c) => c.name.length > 0);
}

export interface ResultColumnSummary {
  min: number | string | null;
  max: number | string | null;
  mean: number | null;
  nullCount: number | null;
}

export function asResultSummary(v: unknown): Record<string, ResultColumnSummary> {
  if (typeof v !== "object" || v === null) return {};
  const out: Record<string, ResultColumnSummary> = {};
  for (const [key, raw] of Object.entries(v as Record<string, unknown>)) {
    if (typeof raw !== "object" || raw === null) continue;
    const s = raw as Record<string, unknown>;
    out[key] = {
      min: num(s.min) ?? str(s.min),
      max: num(s.max) ?? str(s.max),
      mean: num(s.mean) ?? num(s.avg),
      nullCount: num(s.null_count),
    };
  }
  return out;
}
