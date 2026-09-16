import type { ToolResult } from "@/types/chat";

export const TABLE_DISPLAY_ROW_LIMIT = 100;

export type TableCell = string | number | boolean | null;

export interface StandaloneTablePayload {
  resultId: string;
  title: string | null;
  columns: string[];
  rows: TableCell[][];
  rowCount: number;
  displayedCount: number;
  sourceTruncated: boolean;
}

const ID_PATTERN = /^[0-9a-f]{32}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isCell(value: unknown): value is TableCell {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

export function tablePayloadFromToolResult(
  result: ToolResult | undefined,
): StandaloneTablePayload | null {
  if (!result || !isRecord(result.data)) return null;
  const data = result.data;
  if (
    data.status !== "ok" ||
    typeof data.result_id !== "string" ||
    !ID_PATTERN.test(data.result_id) ||
    !(data.title === null || data.title === undefined || (typeof data.title === "string" && data.title.length <= 120)) ||
    !Array.isArray(data.columns) ||
    data.columns.length === 0 ||
    !data.columns.every((column) => typeof column === "string" && column.length > 0) ||
    new Set(data.columns).size !== data.columns.length ||
    !Array.isArray(data.rows) ||
    data.rows.length > TABLE_DISPLAY_ROW_LIMIT ||
    !Number.isInteger(data.row_count) ||
    (data.row_count as number) < 0 ||
    !Number.isInteger(data.displayed_count) ||
    data.displayed_count !== data.rows.length ||
    (data.row_count as number) < data.rows.length ||
    typeof data.source_truncated !== "boolean"
  ) {
    return null;
  }

  const columns = data.columns as string[];
  const rows: TableCell[][] = [];
  for (const row of data.rows) {
    if (
      !Array.isArray(row) ||
      row.length !== columns.length ||
      !row.every(isCell)
    ) {
      return null;
    }
    rows.push(row);
  }

  return {
    resultId: data.result_id,
    title: typeof data.title === "string" && data.title.length > 0 ? data.title : null,
    columns,
    rows,
    rowCount: data.row_count as number,
    displayedCount: data.displayed_count as number,
    sourceTruncated: data.source_truncated,
  };
}
