/** tool_result data(Record<string, unknown>) 안전 파싱 helper. */

import type { ChartSpec } from "@/types/chat";

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

export function asChart(v: unknown): ChartSpec | undefined {
  if (typeof v !== "object" || v === null) return undefined;
  const c = v as Record<string, unknown>;
  if (c.type !== "bar" && c.type !== "line") return undefined;
  if (typeof c.x !== "string") return undefined;
  if (!Array.isArray(c.series) || !Array.isArray(c.categories) || !Array.isArray(c.data)) {
    return undefined;
  }
  return c as unknown as ChartSpec;
}

export type ResultTone = "neutral" | "ok" | "warn" | "block";

export function toneOf(v: unknown): ResultTone {
  return v === "ok" || v === "warn" || v === "block" ? v : "neutral";
}
