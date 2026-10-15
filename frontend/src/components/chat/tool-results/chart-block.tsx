import type { ChartSpec, VisualizationWarning } from "@/types/chat";
import { TYPE_LABEL, chartSummary } from "@/lib/chart-summary";
import { displayCell } from "@/lib/format-cell";
import { AreaChartView } from "./charts/area-chart-view";
import { BarChartView } from "./charts/bar-chart-view";
import { LineChartView } from "./charts/line-chart-view";
import { DataTable, Disclosure } from "../primitives";

/** 검증된 chart v2 payload를 의미 변경 없이 렌더링한다. */
export function ChartBlock({
  chart,
  warnings = [],
  alwaysLegend = false,
  stacked = false,
}: {
  chart: ChartSpec;
  warnings?: VisualizationWarning[];
  alwaysLegend?: boolean;
  stacked?: boolean;
}) {
  return (
    <section
      className="flex flex-col gap-2 rounded border border-line bg-surface p-3"
      aria-label={chart.title ?? `${chart.type === "bar" && stacked ? "누적 막대" : TYPE_LABEL[chart.type]} 차트`}
    >
      {(chart.title || chart.unit) && (
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          {chart.title && <h3 className="font-medium text-ink">{chart.title}</h3>}
          {chart.unit && <span className="text-2xs text-ink-2">단위: {chart.unit}</span>}
        </div>
      )}
      <p className="sr-only">{chartSummary(chart, stacked)}</p>
      <div className="thin-scroll overflow-x-auto">
        <div className="min-w-[32rem]">
          {chart.type === "bar" && <BarChartView chart={chart} alwaysLegend={alwaysLegend} stacked={stacked} />}
          {chart.type === "line" && <LineChartView chart={chart} alwaysLegend={alwaysLegend} />}
          {chart.type === "area" && <AreaChartView chart={chart} alwaysLegend={alwaysLegend} />}
        </div>
      </div>
      <Disclosure summary="차트 데이터 표로 보기" dense>
        <p className="mb-2 text-2xs text-ink-2">{chart.x_label ?? chart.x} · {chart.y_label ?? "값"}{chart.unit ? ` · 단위: ${chart.unit}` : ""}</p>
        <DataTable columns={[chart.x_label ?? chart.x, ...chart.series.map(s => s.label)]}
          rows={chart.data.map(row => [row[chart.x], ...chart.series.map(s => row[s.key])].map(value => value == null || typeof value === "number" ? displayCell(value) : String(value)))} />
      </Disclosure>
      {warnings.map((warning) => (
        <p key={`${warning.code}:${warning.message}`} className="text-2xs text-warn-ink">
          {warning.code === "SOURCE_TRUNCATED"
            ? `저장된 조회 결과 범위 안내: ${warning.message}`
            : warning.message}
        </p>
      ))}
    </section>
  );
}
