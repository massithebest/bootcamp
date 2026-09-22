import type { ChartSpec } from "@/types/chat";

export const TYPE_LABEL = { bar: "막대", line: "선", area: "영역" } as const;

/** 스크린 리더용 간결한 요약. 값 전체는 아래 데이터 표에 있다. */
export function chartSummary(chart: ChartSpec): string {
  const label = TYPE_LABEL[chart.type];
  const xs = chart.categories;
  const range = xs.length > 1 ? `${xs[0]}부터 ${xs[xs.length - 1]}까지` : String(xs[0] ?? "");
  return `${label} 차트, ${chart.x_label ?? chart.x} ${xs.length}개 구간(${range}), 계열 ${chart.series.length}개: ${chart.series.map((s) => s.label).join(", ")}.`;
}
