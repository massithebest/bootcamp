/**
 * `present` Tool이 렌더하는 component library.
 *
 * `defineGenerativeComponents`는 `"use generative"` compiler 없이는 실행 시 예외를 던지므로
 * 쓰지 않고, 같은 `GenerativeUILibrary` 형태의 일반 객체를 만든다(Python Backend가 Tool을
 * 실행하므로 compiler의 server split이 필요 없다).
 */
import {
  defaultGenerativeUILibrary,
  type GenerativeUILibrary,
} from "@assistant-ui/react-generative-ui";

import { QueryChart } from "./query-chart";
import { QueryTable } from "./query-table";
import { ResultNotice } from "./message";
import { SimulationSummary } from "./simulation-summary";
import { SqlPreview } from "./sql-preview";
import {
  BASE_COMPONENT_NAMES,
  queryChartProps,
  queryTableProps,
  simulationSummaryProps,
  sqlPreviewProps,
} from "./vocabulary";

function invalid(name: string) {
  return <ResultNotice tone="alert">{name} 표시 설정이 올바르지 않아 표시하지 못했습니다.</ResultNotice>;
}

const base = Object.fromEntries(
  BASE_COMPONENT_NAMES.map((name) => [name, defaultGenerativeUILibrary[name]]),
) as GenerativeUILibrary;

export const generativeLibrary: GenerativeUILibrary = {
  ...base,
  SqlPreview: {
    description: "실행한 SQL 원문(기본 접힘).",
    properties: sqlPreviewProps,
    render: (props) => {
      const parsed = sqlPreviewProps.safeParse(props);
      return parsed.success ? <SqlPreview {...parsed.data} /> : invalid("SqlPreview");
    },
  },
  QueryChart: {
    description: "저장 결과를 서버가 집계한 차트. resultId와 컬럼 설정만 지정한다.",
    properties: queryChartProps,
    render: (props) => {
      const parsed = queryChartProps.safeParse(props);
      return parsed.success ? <QueryChart {...parsed.data} /> : invalid("QueryChart");
    },
  },
  QueryTable: {
    description: "저장 결과를 페이지 단위로 보여 주는 표. resultId만 지정한다.",
    properties: queryTableProps,
    render: (props) => {
      const parsed = queryTableProps.safeParse(props);
      return parsed.success ? <QueryTable {...parsed.data} /> : invalid("QueryTable");
    },
  },
  SimulationSummary: {
    description: "시뮬레이션 시나리오·요약·KPI. 자식으로 QueryChart/QueryTable만 둘 수 있다.",
    properties: simulationSummaryProps,
    render: (props) => {
      const parsed = simulationSummaryProps.safeParse(props);
      return parsed.success
        ? <SimulationSummary {...parsed.data}>{props.children}</SimulationSummary>
        : invalid("SimulationSummary");
    },
  },
};
