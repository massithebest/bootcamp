/**
 * `present_*` Tool 인자의 prop schema(Zod).
 * Backend의 `present_*` Tool 인자와 같은 이름·타입을 유지한다(계약 테스트가 비교한다).
 * 원본 행·차트 data 배열·HTML·URL·action prop은 받지 않는다.
 */
import { z } from "zod";

import { RESULT_ID_PATTERN } from "@/types/query-result";

export const resultIdSchema = z.string().regex(RESULT_ID_PATTERN);

export const sqlPreviewArgs = z.object({
  sql: z.string().max(20_000),
  title: z.string().max(120).optional(),
});

export const chartArgs = z.object({
  result_id: resultIdSchema,
  chart_type: z.enum(["bar", "line", "area"]),
  x_column: z.string().max(200),
  y_column: z.string().max(200),
  group_by_column: z.string().max(200).nullable().optional(),
  aggregation: z.enum(["sum", "avg", "count", "min", "max"]).optional(),
  title: z.string().max(120).optional(),
});

export const tableArgs = z.object({
  result_id: resultIdSchema,
  columns: z.array(z.string().max(200)).max(50).optional(),
  title: z.string().max(120).optional(),
});

export const simulationArgs = z.object({
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
  result_id: resultIdSchema.optional(),
});
