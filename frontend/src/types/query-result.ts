/**
 * Result Store 기반 조회 API(`/api/query-results/{resultId}/…`) 응답 계약.
 * 전체 행은 preview에 없고, 표는 page 단위로만, 차트는 서버가 집계한 결과만 받는다.
 */

import type { ChartSpec, VisualizationWarning } from "./chat";

export const RESULT_ID_PATTERN = /^[0-9a-f]{32}$/;

export type ChartType = "bar" | "line" | "area";
export type Aggregation = "sum" | "avg" | "count" | "min" | "max";

export interface QueryColumn {
  name: string;
  dtype: string;
  role: string | null;
}

export interface QueryTablePage {
  result_id: string;
  page: number;
  page_size: number;
  row_count: number;
  filtered_row_count: number;
  source_truncated: boolean;
  columns: QueryColumn[];
  rows: (string | number | boolean | null)[][];
}

export interface QueryChartResponse {
  result_id: string;
  chart: ChartSpec;
  warnings: VisualizationWarning[];
}

export interface QueryChartRequest {
  resultId: string;
  chartType: ChartType;
  xColumn: string;
  yColumn: string;
  groupByColumn?: string | null;
  aggregation?: Aggregation;
  title?: string;
}

export interface QueryTableRequest {
  resultId: string;
  page: number;
  pageSize: number;
  columns?: readonly string[];
  search?: string;
  sortColumn?: string;
  sortDirection?: "asc" | "desc";
}
