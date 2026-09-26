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
import {
  type QueryChartRequest,
  type QueryChartResponse,
  type QueryTablePage,
  type QueryTableRequest,
} from "@/types/query-result";

import { isRecord, parseQueryChartResponse, parseQueryTablePage } from "./query-result-parser";
import { RequestPool } from "./query-result-request-pool";

// 기존 소비자의 import 경로와 공개 API를 유지한다.
export {
  QUERY_TABLE_MAX_PAGE_SIZE,
  parseWarnings,
  parseChartSpec,
  parseQueryTablePage,
  parseQueryChartResponse,
} from "./query-result-parser";

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
