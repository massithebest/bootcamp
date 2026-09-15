import type { ChartSpec } from "@/types/chat";
import { BarChartView } from "./charts/bar-chart-view";
import { LineChartView } from "./charts/line-chart-view";

/** `chart.type` 별 뷰 스위치. `chart` 는 백엔드가 결정론적으로 조립한 값이다. */
export function ChartBlock({ chart }: { chart: ChartSpec }) {
  return (
    <div className="flex flex-col gap-1">
      {chart.type === "bar" && <BarChartView chart={chart} />}
      {chart.type === "line" && <LineChartView chart={chart} />}
      {chart.truncated && (
        <p className="text-2xs text-ink-3">
          상위 {chart.categories.length}개만 표시했습니다. 그 외{" "}
          {chart.hiddenCount}건은 표에서 확인하세요.
        </p>
      )}
    </div>
  );
}
