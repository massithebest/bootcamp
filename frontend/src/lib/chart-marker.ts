const VISUALIZATION_ID_PATTERN = /^[0-9a-f]{32}$/;

export type ChartMarkerParseResult =
  | { type: "valid"; visualizationId: string }
  | { type: "incomplete" }
  | { type: "invalid" };

export function parseChartMarker(source: string): ChartMarkerParseResult {
  let value: unknown;
  try {
    value = JSON.parse(source.trim());
  } catch {
    return { type: "incomplete" };
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return { type: "invalid" };
  }
  const record = value as Record<string, unknown>;
  if (
    Object.keys(record).length !== 1 ||
    typeof record.visualization_id !== "string" ||
    !VISUALIZATION_ID_PATTERN.test(record.visualization_id)
  ) {
    return { type: "invalid" };
  }
  return { type: "valid", visualizationId: record.visualization_id };
}
