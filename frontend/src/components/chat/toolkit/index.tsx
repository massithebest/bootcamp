import { defineToolkit } from "@assistant-ui/react";

/** 실행 과정 그룹 안에 표시하는 Backend Tool. 이름이 일치하는 호출에 같은 결과 카드를 연결한다. */
export const GROUPED_TOOL_NAMES = [
  "execute_sql",
  "search_documents",
  "list_simulation",
  "run_simulation",
  "list_tables",
  "describe_table",
  "list_kpis",
  "get_kpi",
  "list_recipes",
  "get_recipe",
  "get_result_summary",
  "get_result_page",
] as const;

const groupedTools = Object.fromEntries(
  GROUPED_TOOL_NAMES.map((name) => [name, { type: "backend" as const, render: RegisteredToolUI }]),
) as Record<(typeof GROUPED_TOOL_NAMES)[number], { type: "backend"; render: typeof RegisteredToolUI }>;

import {
  PresentChartToolUI,
  PresentSimulationToolUI,
  PresentSqlPreviewToolUI,
  PresentTableToolUI,
} from "../generative/present-tool-uis";
import { RegisteredToolUI } from "./tool-ui";
import { TableToolUI } from "../tool-results/table-tool-ui";
import { VisualizationToolUI } from "../tool-results/visualization-tool-ui";

/**
 * Backend Tool 실행은 그대로 두고 이름이 일치하는 호출에 UI만 연결한다.
 *
 * - `present_sql_preview`·`present_chart`·`present_table`·`present_simulation`:
 *   각 Tool이 받은 scalar 인자를 그대로 컴포넌트 prop으로 매핑한다(`RESULT_UI_MODE=present`).
 * - `prepare_table`·`prepare_visualization`: 과거 메시지와 `RESULT_UI_MODE=legacy` 호환.
 */
export const productionPlanningToolkit = defineToolkit({
  ...groupedTools,
  present_sql_preview: {
    type: "backend",
    display: "standalone",
    render: PresentSqlPreviewToolUI,
  },
  present_chart: {
    type: "backend",
    display: "standalone",
    render: PresentChartToolUI,
  },
  present_table: {
    type: "backend",
    display: "standalone",
    render: PresentTableToolUI,
  },
  present_simulation: {
    type: "backend",
    display: "standalone",
    render: PresentSimulationToolUI,
  },
  prepare_table: {
    type: "backend",
    display: "standalone",
    render: TableToolUI,
  },
  prepare_visualization: {
    type: "backend",
    display: "standalone",
    render: VisualizationToolUI,
  },
});
