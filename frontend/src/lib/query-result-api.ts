/**
 * Result Store 조회 API 클라이언트.
 *
 *   GET /api/query-results/{resultId}/table   — 서버 page 단위 표
 *   GET /api/query-results/{resultId}/chart   — 서버가 검증·집계한 chart
 *
 * 응답은 엄격히 검증하며 실패는 `QueryResultFetchError`의 안전한 종류로만 노출한다.
 * 같은 요청은 진행 중인 fetch만 공유하고, 구독자가 모두 사라지면 abort한다.
 * 완료 응답은 서버의 private TTL cache 정책에 맡긴다.
 */

import { API_BASE_URL } from "@/lib/chat-api";
import type { ChartSpec, VisualizationWarning } from "@/types/chat";
import {
  RESULT_ID_PATTERN,
  type QueryChartRequest,
  type QueryChartResponse,
  type QueryColumn,
  type QueryTablePage,
  type QueryTableRequest,
} from "@/types/query-result";

export const QUERY_TABLE_MAX_PAGE_SIZE = 100;

export type QueryResultErrorKind =
  | "not-found"
  | "invalid-request"
  | "network"
  | "invalid-response"
  | "aborted";

export class QueryResultFetchError extends Error {
  constructor(
    public readonly kind: QueryResultErrorKind,
    message: string,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "QueryResultFetchError";
  }
}

const NETWORK_MESSAGE = "결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";
const NOT_FOUND_MESSAGE =
  "결과를 찾을 수 없습니다. 만료되었거나 접근할 수 없는 결과입니다. 다시 조회해 주세요.";
const INVALID_RESPONSE_MESSAGE = "결과 응답 형식이 올바르지 않습니다.";

function isRecord(value: unknown): value is Record<string, unknown> {
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

export function buildTableUrl(request: QueryTableRequest): string {
  const params = new URLSearchParams({
    page: String(request.page),
    page_size: String(request.pageSize),
  });
  for (const column of request.columns ?? []) params.append("columns", column);
  if (request.search) params.set("search", request.search);
  if (request.sortColumn) params.set("sort_column", request.sortColumn);
  if (request.sortDirection) params.set("sort_direction", request.sortDirection);
  return `${API_BASE_URL}/api/query-results/${encodeURIComponent(request.resultId)}/table?${params}`;
}

export function buildChartUrl(request: QueryChartRequest): string {
  const params = new URLSearchParams({
    chart_type: request.chartType,
    x_column: request.xColumn,
    y_column: request.yColumn,
  });
  if (request.groupByColumn) params.set("group_by_column", request.groupByColumn);
  if (request.aggregation) params.set("aggregation", request.aggregation);
  if (request.title) params.set("title", request.title);
  return `${API_BASE_URL}/api/query-results/${encodeURIComponent(request.resultId)}/chart?${params}`;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function readError(response: Response): Promise<QueryResultFetchError> {
  if (response.status === 404) {
    return new QueryResultFetchError("not-found", NOT_FOUND_MESSAGE, "RESULT_NOT_FOUND");
  }
  if (response.status === 422 || response.status === 400) {
    let code: string | undefined;
    let message = "요청한 표시 설정을 적용할 수 없습니다.";
    try {
      const body: unknown = await response.json();
      const detail = isRecord(body) ? body.detail : null;
      if (isRecord(detail)) {
        if (typeof detail.code === "string") code = detail.code;
        if (typeof detail.message === "string" && detail.message.length <= 300) {
          message = detail.message;
        }
      }
    } catch {
      /* 안전한 기본 문구를 유지한다. */
    }
    return new QueryResultFetchError("invalid-request", message, code);
  }
  return new QueryResultFetchError("network", NETWORK_MESSAGE);
}

async function fetchJson<T>(
  url: string,
  parse: (value: unknown) => T | null,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { signal, credentials: "include" });
  } catch (error) {
    if (isAbortError(error)) {
      throw new QueryResultFetchError("aborted", "결과 조회가 취소되었습니다.");
    }
    throw new QueryResultFetchError("network", NETWORK_MESSAGE);
  }
  if (!response.ok) throw await readError(response);
  let raw: unknown;
  try {
    raw = await response.json();
  } catch {
    throw new QueryResultFetchError("invalid-response", INVALID_RESPONSE_MESSAGE);
  }
  const parsed = parse(raw);
  if (!parsed) throw new QueryResultFetchError("invalid-response", INVALID_RESPONSE_MESSAGE);
  return parsed;
}

export function fetchQueryTable(
  request: QueryTableRequest,
  options: { signal?: AbortSignal } = {},
): Promise<QueryTablePage> {
  return fetchJson(buildTableUrl(request), parseQueryTablePage, options.signal);
}

export function fetchQueryChart(
  request: QueryChartRequest,
  options: { signal?: AbortSignal } = {},
): Promise<QueryChartResponse> {
  return fetchJson(buildChartUrl(request), parseQueryChartResponse, options.signal);
}

/* ---- 진행 중 요청 공유·abort ---- */

interface InFlight<T> {
  controller: AbortController;
  promise: Promise<T>;
  subscribers: number;
  abortTimer: ReturnType<typeof setTimeout> | null;
}

class RequestPool<T> {
  private readonly inFlight = new Map<string, InFlight<T>>();

  clear(): void {
    for (const request of this.inFlight.values()) request.controller.abort();
    this.inFlight.clear();
  }

  acquire(key: string, run: (signal: AbortSignal) => Promise<T>): {
    promise: Promise<T>;
    release: () => void;
  } {
    let request = this.inFlight.get(key);
    if (request?.controller.signal.aborted) {
      this.inFlight.delete(key);
      request = undefined;
    }
    if (!request) {
      const controller = new AbortController();
      const next: InFlight<T> = {
        controller,
        subscribers: 0,
        abortTimer: null,
        promise: Promise.resolve(null as never),
      };
      next.promise = run(controller.signal).then(
        (value) => {
          if (this.inFlight.get(key) === next) this.inFlight.delete(key);
          return value;
        },
        (error: unknown) => {
          if (this.inFlight.get(key) === next) this.inFlight.delete(key);
          throw error;
        },
      );
      this.inFlight.set(key, next);
      request = next;
    }
    if (request.abortTimer !== null) {
      clearTimeout(request.abortTimer);
      request.abortTimer = null;
    }
    request.subscribers += 1;
    const current = request;
    let released = false;
    return {
      promise: current.promise,
      release: () => {
        if (released) return;
        released = true;
        current.subscribers -= 1;
        if (current.subscribers === 0 && this.inFlight.get(key) === current) {
          current.abortTimer = setTimeout(() => {
            current.abortTimer = null;
            if (current.subscribers === 0 && this.inFlight.get(key) === current) {
              current.controller.abort();
              this.inFlight.delete(key);
            }
          }, 0);
        }
      },
    };
  }
}

const chartPool = new RequestPool<QueryChartResponse>();
const tablePool = new RequestPool<QueryTablePage>();

export function chartRequestKey(request: QueryChartRequest): string {
  return JSON.stringify([
    request.resultId,
    request.chartType,
    request.xColumn,
    request.yColumn,
    request.groupByColumn ?? "",
    request.aggregation ?? "",
    request.title ?? "",
  ]);
}

export function tableRequestKey(request: QueryTableRequest): string {
  return JSON.stringify([
    request.resultId,
    request.page,
    request.pageSize,
    request.columns ?? null,
    request.search ?? "",
    request.sortColumn ?? "",
    request.sortDirection ?? "",
  ]);
}

export function acquireQueryChart(request: QueryChartRequest) {
  return chartPool.acquire(chartRequestKey(request), (signal) =>
    fetchQueryChart(request, { signal }),
  );
}

export function acquireQueryTable(request: QueryTableRequest) {
  return tablePool.acquire(tableRequestKey(request), (signal) =>
    fetchQueryTable(request, { signal }),
  );
}

/** 테스트와 진행 중 요청 강제 취소용. */
export function clearQueryResultCache(): void {
  chartPool.clear();
  tablePool.clear();
}
