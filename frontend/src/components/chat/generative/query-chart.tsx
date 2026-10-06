import { useMemo, useState } from "react";

import { useQueryChart } from "@/hooks/use-query-result";
import type { ChartType, Aggregation } from "@/types/query-result";
import { ChartBlock } from "../tool-results/chart-block";
import { ResultNotice, RetryButton } from "./message";

export interface QueryChartProps {
  resultId: string;
  chartType: ChartType;
  barMode?: "grouped" | "stacked";
  xColumn: string;
  yColumn: string;
  groupByColumn?: string | null;
  aggregation?: Aggregation;
  title?: string;
}

/** resultId와 표시 설정으로 서버가 집계한 chart를 조회해 그린다. 원본 데이터는 받지 않는다. */
export function QueryChart(props: QueryChartProps) {
  const { resultId, chartType, barMode, xColumn, yColumn, groupByColumn, aggregation, title } = props;
  const [retryKey, setRetryKey] = useState(0);
  const request = useMemo(
    () => ({ resultId, chartType, xColumn, yColumn, groupByColumn, aggregation, title }),
    [resultId, chartType, xColumn, yColumn, groupByColumn, aggregation, title],
  );
  const state = useQueryChart(request, retryKey);

  if (state.type === "loading") {
    return (
      <ResultNotice loading className="min-h-64 animate-pulse motion-reduce:animate-none">
        <span>차트를 불러오는 중…</span>
      </ResultNotice>
    );
  }
  if (state.type === "success") {
    const { chart, warnings } = state.value;
    if (chart.data.length === 0) {
      return <ResultNotice>차트로 표시할 데이터가 없습니다. 조회 조건을 넓혀 다시 요청해 주세요.</ResultNotice>;
    }
    return <ChartBlock chart={chart} warnings={warnings} alwaysLegend stacked={barMode === "stacked"} />;
  }
  if (state.type === "not-found") {
    return <ResultNotice tone="alert">{state.message}</ResultNotice>;
  }
  if (state.type === "invalid-request") {
    return (
      <ResultNotice tone="alert">
        <span>이 차트 설정을 적용할 수 없습니다. {state.message}</span>
        <span className="text-2xs text-ink-3">표로 확인하거나 다른 컬럼으로 다시 요청해 주세요.</span>
      </ResultNotice>
    );
  }
  return (
    <ResultNotice tone="alert">
      <span>{state.message}</span>
      <RetryButton onClick={() => setRetryKey((value) => value + 1)} />
    </ResultNotice>
  );
}
