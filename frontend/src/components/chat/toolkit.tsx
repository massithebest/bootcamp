import { defineToolkit } from "@assistant-ui/react";

import { VisualizationToolUI } from "./tool-results/visualization-tool-ui";
import { TableToolUI } from "./tool-results/table-tool-ui";

/** Backend Tool 실행은 그대로 두고 이름이 일치하는 호출에 UI만 연결한다. */
export const productionPlanningToolkit = defineToolkit({
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
