import type { ChartSpec, VisualizationWarning } from "@/types/chat";
import { BarChartView } from "./charts/bar-chart-view";
import { LineChartView } from "./charts/line-chart-view";

/** 검증된 chart v2 payload를 의미 변경 없이 렌더링한다. */
export function ChartBlock({
  chart,
  warnings = [],
}: {
  chart: ChartSpec;
  warnings?: VisualizationWarning[];
}) {
  return (
    <section
      className="flex flex-col gap-2 rounded border border-line bg-surface p-3"
      aria-label={chart.title ?? `${chart.type === "line" ? "선" : "막대"} 차트`}
    >
      {(chart.title || chart.unit) && (
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          {chart.title && <h4 className="font-medium text-ink">{chart.title}</h4>}
          {chart.unit && <span className="text-2xs text-ink-3">단위: {chart.unit}</span>}
        </div>
      )}
      <div className="thin-scroll overflow-x-auto">
        <div className="min-w-[32rem]">
          {chart.type === "bar" && <BarChartView chart={chart} />}
          {chart.type === "line" && <LineChartView chart={chart} />}
        </div>
      </div>
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
