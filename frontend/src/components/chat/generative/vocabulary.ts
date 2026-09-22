/**
 * `present`가 받는 도메인 component의 prop schema(Zod).
 * Backend의 `present` vocabulary와 같은 이름·타입을 유지한다(계약 테스트가 비교한다).
 * 원본 행·차트 data 배열·HTML·URL·action prop은 받지 않는다.
 */
import { z } from "zod";

import { RESULT_ID_PATTERN } from "@/types/query-result";

/** 기본 package vocabulary에서 허용하는 읽기 전용 subset. */
export const BASE_COMPONENT_NAMES = [
  "Card",
] as const;

export const CUSTOM_COMPONENT_NAMES = [
  "SqlPreview",
  "QueryChart",
  "QueryTable",
  "SimulationSummary",
] as const;

export const resultIdSchema = z.string().regex(RESULT_ID_PATTERN);

export const sqlPreviewProps = z.object({
  sql: z.string().max(20_000),
  title: z.string().max(120).optional(),
});

export const queryChartProps = z.object({
  resultId: resultIdSchema,
  chartType: z.enum(["bar", "line", "area"]),
  xColumn: z.string().max(200),
  yColumn: z.string().max(200),
  groupByColumn: z.string().max(200).nullable().optional(),
  aggregation: z.enum(["sum", "avg", "count", "min", "max"]).optional(),
  title: z.string().max(120).optional(),
});

export const queryTableProps = z.object({
  resultId: resultIdSchema,
  columns: z.array(z.string().max(200)).max(50).optional(),
  title: z.string().max(120).optional(),
});

export const simulationSummaryProps = z.object({
  scenario: z.string().max(200),
  summary: z.string().max(2000),
  kpis: z
    .array(
      z.object({
        label: z.string().max(80),
        value: z.union([z.string().max(80), z.number().finite()]),
        unit: z.string().max(20).optional(),
      }),
    )
    .max(12),
  resultId: resultIdSchema.optional(),
});
