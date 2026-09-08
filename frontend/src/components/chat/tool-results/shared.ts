/** tool_result data(Record<string, unknown>) 안전 파싱 helper. */

export function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

export function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
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
