/** Result Store 응답의 순수 검증. 네트워크와 요청 수명에 의존하지 않는다. */
import type { ChartSpec, VisualizationWarning } from "@/types/chat";
import {
  RESULT_ID_PATTERN,
  type QueryChartResponse,
  type QueryColumn,
  type QueryTablePage,
} from "@/types/query-result";

export const QUERY_TABLE_MAX_PAGE_SIZE = 100;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isCategory(value: unknown): value is string | number {
  return (
    typeof value === "string" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

export function parseWarnings(value: unknown): VisualizationWarning[] | null {
  if (!Array.isArray(value)) return null;
  const warnings: VisualizationWarning[] = [];
  for (const warning of value) {
    if (
      !isRecord(warning) ||
      typeof warning.code !== "string" ||
      typeof warning.message !== "string"
    ) {
      return null;
    }
    warnings.push({ code: warning.code, message: warning.message });
  }
  return warnings;
}

/** present_chart/차트 조회 API가 공유하는 chart 검증. bar/line/area만 허용한다. */
export function parseChartSpec(
  value: unknown,
  allowed: readonly ChartSpec["type"][] = ["bar", "line", "area"],
): ChartSpec | null {
  if (!isRecord(value) || !allowed.includes(value.type as ChartSpec["type"])) {
    return null;
  }
  if (
    typeof value.x !== "string" ||
    !Array.isArray(value.series) ||
    value.series.length === 0 ||
    value.series.length > 8 ||
    !Array.isArray(value.categories) ||
    value.categories.length > 500 ||
    !Array.isArray(value.data) ||
    value.data.length !== value.categories.length ||
    !isNullableString(value.title) ||
    !isNullableString(value.x_label) ||
    !isNullableString(value.y_label) ||
    !isNullableString(value.unit)
  ) {
    return null;
  }

  const series: ChartSpec["series"] = [];
  const keys = new Set<string>();
  for (const raw of value.series) {
    if (
      !isRecord(raw) ||
      typeof raw.key !== "string" ||
      !raw.key ||
      keys.has(raw.key) ||
      typeof raw.label !== "string"
    ) {
      return null;
    }
    keys.add(raw.key);
    series.push({ key: raw.key, label: raw.label });
  }

  if (!value.categories.every(isCategory)) return null;
  const data: Record<string, unknown>[] = [];
  for (let index = 0; index < value.data.length; index += 1) {
    const row = value.data[index];
    if (!isRecord(row) || row[value.x] !== value.categories[index]) return null;
    if (Object.keys(row).some((key) => key !== value.x && !keys.has(key))) return null;
    for (const key of keys) {
      const point = row[key];
      if (
        point !== null &&
        !(typeof point === "number" && Number.isFinite(point))
      ) {
        return null;
      }
    }
    data.push(row);
  }

  return {
    type: value.type as ChartSpec["type"],
    x: value.x,
    series,
    categories: value.categories,
    data,
    title: value.title,
    x_label: value.x_label,
    y_label: value.y_label,
    unit: value.unit,
  };
}

function parseColumns(value: unknown): QueryColumn[] | null {
  if (!Array.isArray(value)) return null;
  const columns: QueryColumn[] = [];
  for (const raw of value) {
    if (
      !isRecord(raw) ||
      typeof raw.name !== "string" ||
      typeof raw.dtype !== "string" ||
      (raw.role !== null && typeof raw.role !== "string")
    ) {
      return null;
    }
    columns.push({ name: raw.name, dtype: raw.dtype, role: raw.role });
  }
  return columns;
}

function isCell(value: unknown): value is string | number | boolean | null {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

export function parseQueryTablePage(value: unknown): QueryTablePage | null {
  if (
    !isRecord(value) ||
    value.status !== "ok" ||
    typeof value.result_id !== "string" ||
    !RESULT_ID_PATTERN.test(value.result_id) ||
    !Number.isInteger(value.page) ||
    (value.page as number) < 1 ||
    !Number.isInteger(value.page_size) ||
    (value.page_size as number) < 1 ||
    (value.page_size as number) > QUERY_TABLE_MAX_PAGE_SIZE ||
    !Number.isInteger(value.row_count) ||
    (value.row_count as number) < 0 ||
    !Number.isInteger(value.filtered_row_count) ||
    (value.filtered_row_count as number) < 0 ||
    (value.filtered_row_count as number) > (value.row_count as number) ||
    typeof value.source_truncated !== "boolean" ||
    !Array.isArray(value.rows) ||
    value.rows.length > (value.page_size as number) ||
    value.rows.length > (value.filtered_row_count as number)
  ) {
    return null;
  }
  const columns = parseColumns(value.columns);
  if (!columns) return null;
  const rows: QueryTablePage["rows"] = [];
  for (const row of value.rows) {
    if (!Array.isArray(row) || row.length !== columns.length || !row.every(isCell)) {
      return null;
    }
    rows.push(row);
  }
  return {
    result_id: value.result_id,
    page: value.page as number,
    page_size: value.page_size as number,
    row_count: value.row_count as number,
    filtered_row_count: value.filtered_row_count as number,
    source_truncated: value.source_truncated,
    columns,
    rows,
  };
}

export function parseQueryChartResponse(value: unknown): QueryChartResponse | null {
  if (
    !isRecord(value) ||
    value.status !== "ok" ||
    typeof value.result_id !== "string" ||
    !RESULT_ID_PATTERN.test(value.result_id)
  ) {
    return null;
  }
  const chart = parseChartSpec(value.chart, ["bar", "line", "area"]);
  const warnings = parseWarnings(value.warnings);
  if (!chart || !warnings) return null;
  return { result_id: value.result_id, chart, warnings };
}
