const VISUALIZATION_ID_PATTERN = /^[0-9a-f]{32}$/;

export function isVisualizationId(value: unknown): value is string {
  return typeof value === "string" && VISUALIZATION_ID_PATTERN.test(value);
}

/** Backend Tool result wrapper 또는 원본 payload에서 검증된 ID만 읽는다. */
export function visualizationIdFromToolResult(result: unknown): string | null {
  if (!isRecord(result)) return null;
  const payload = isRecord(result.data) ? result.data : result;
  return isVisualizationId(payload.visualization_id) ? payload.visualization_id : null;
}

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
    !isVisualizationId(record.visualization_id)
  ) {
    return { type: "invalid" };
  }
  return { type: "valid", visualizationId: record.visualization_id };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
