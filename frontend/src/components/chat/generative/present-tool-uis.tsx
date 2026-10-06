import type { ToolCallMessagePartComponent } from "@assistant-ui/react";

import type { ToolResult } from "@/types/chat";
import { toolResultError } from "@/lib/tool-result";
import { QueryChart } from "./query-chart";
import { QueryTable } from "./query-table";
import { ResultNotice } from "./message";
import { SimulationSummary } from "./simulation-summary";
import { SqlPreview } from "./sql-preview";
import { chartArgs, simulationArgs, sqlPreviewArgs, tableArgs } from "./vocabulary";

/**
 * Backend가 검증한 `present_*` Tool 인자를 실제 화면 컴포넌트로 그린다.
 * `present_*`는 각각 스칼라 인자만 받으므로 $type 트리 파싱 없이
 * Tool 이름이 곧 컴포넌트를 정한다.
 */

function invalid(name: string) {
  return <ResultNotice tone="alert">{name} 표시 설정이 올바르지 않아 표시하지 못했습니다.</ResultNotice>;
}

function presentStatusNotice(props: { status: { type: string; reason?: string }; result?: ToolResult; isError?: boolean }) {
  const { status, result, isError } = props;
  if (status.type === "running") {
    return <ResultNotice loading>결과 화면을 구성하는 중…</ResultNotice>;
  }
  if (status.type === "incomplete") {
    return (
      <ResultNotice tone={status.reason === "cancelled" ? "neutral" : "alert"}>
        {status.reason === "cancelled" ? "결과 화면 구성이 중단되었습니다." : "결과 화면을 구성하지 못했습니다."}
      </ResultNotice>
    );
  }
  if (status.type === "requires-action") {
    return <ResultNotice>결과 화면을 표시하려면 응답이 필요합니다.</ResultNotice>;
  }
  const error = result ? toolResultError(result) : null;
  if (isError || error) {
    return <ResultNotice tone="alert">{error ?? "결과 화면을 구성하지 못했습니다."}</ResultNotice>;
  }
  return null;
}

export const PresentSqlPreviewToolUI: ToolCallMessagePartComponent<Record<string, unknown>, ToolResult> = (
  props,
) => {
  const notice = presentStatusNotice(props);
  if (notice) return notice;
  const parsed = sqlPreviewArgs.safeParse(props.args);
  return parsed.success
    ? <SqlPreview sql={parsed.data.sql} title={parsed.data.title} />
    : invalid("present_sql_preview");
};

export const PresentChartToolUI: ToolCallMessagePartComponent<Record<string, unknown>, ToolResult> = (
  props,
) => {
  const notice = presentStatusNotice(props);
  if (notice) return notice;
  const parsed = chartArgs.safeParse(props.args);
  return parsed.success
    ? (
      <QueryChart
        resultId={parsed.data.result_id}
        chartType={parsed.data.chart_type}
        barMode={parsed.data.bar_mode}
        xColumn={parsed.data.x_column}
        yColumn={parsed.data.y_column}
        groupByColumn={parsed.data.group_by_column}
        aggregation={parsed.data.aggregation}
        title={parsed.data.title}
      />
    )
    : invalid("present_chart");
};

export const PresentTableToolUI: ToolCallMessagePartComponent<Record<string, unknown>, ToolResult> = (
  props,
) => {
  const notice = presentStatusNotice(props);
  if (notice) return notice;
  const parsed = tableArgs.safeParse(props.args);
  return parsed.success
    ? <QueryTable resultId={parsed.data.result_id} columns={parsed.data.columns} title={parsed.data.title} />
    : invalid("present_table");
};

export const PresentSimulationToolUI: ToolCallMessagePartComponent<Record<string, unknown>, ToolResult> = (
  props,
) => {
  const notice = presentStatusNotice(props);
  if (notice) return notice;
  const parsed = simulationArgs.safeParse(props.args);
  return parsed.success
    ? (
      <SimulationSummary
        scenario={parsed.data.scenario}
        summary={parsed.data.summary}
        kpis={parsed.data.kpis}
        resultId={parsed.data.result_id}
      />
    )
    : invalid("present_simulation");
};
