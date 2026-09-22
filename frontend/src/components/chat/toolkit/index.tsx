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

import { PresentToolUI } from "../generative/present-tool-ui";
import { RegisteredToolUI } from "./tool-ui";
import { TableToolUI } from "../tool-results/table-tool-ui";
import { VisualizationToolUI } from "../tool-results/visualization-tool-ui";

/**
 * Backend Tool 실행은 그대로 두고 이름이 일치하는 호출에 UI만 연결한다.
 *
 * - `present`: 모델이 조합한 `$type` 트리(SqlPreview·QueryChart·QueryTable·SimulationSummary 등).
 * - `prepare_table`·`prepare_visualization`: 과거 메시지와 `RESULT_UI_MODE=legacy` 호환.
 */
export const productionPlanningToolkit = defineToolkit({
  ...groupedTools,
  present: {
    type: "backend",
    display: "standalone",
    render: PresentToolUI,
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
