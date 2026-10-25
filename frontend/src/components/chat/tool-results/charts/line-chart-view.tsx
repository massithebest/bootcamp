import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { ChartSpec } from "@/types/chat";
import { LINE_DASHES, lineDot } from "./chart-style";
import { formatYAxisTick } from "./axis-format";

const PALETTE = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function LineChartView({
  chart,
  alwaysLegend = false,
}: {
  chart: ChartSpec;
  alwaysLegend?: boolean;
}) {
  const reduced = useReducedMotion();
  const config: ChartConfig = Object.fromEntries(
    chart.series.map((s, i) => [
      s.key,
      { label: s.label, color: PALETTE[i % PALETTE.length] },
    ]),
  );

  return (
    <ChartContainer config={config} className="h-[16.5rem] w-full">
      <LineChart data={chart.data} margin={{ top: 20, left: 12, right: chart.y_label ? 88 : 76, bottom: 12 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey={chart.x}
          tickLine={false}
          axisLine={false}
          tickMargin={22}
          height={chart.x_label ? 78 : undefined}
          label={
            chart.x_label
              ? { value: chart.x_label, position: "insideBottom", offset: 12 }
              : undefined
          }
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={4}
          width={chart.y_label ? 76 : 64}
          tickFormatter={formatYAxisTick}
          label={
            chart.y_label
              ? { value: chart.y_label, angle: -90, position: "insideLeft", textAnchor: "middle" }
              : undefined
          }
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        {(alwaysLegend || chart.series.length > 1) && <ChartLegend wrapperStyle={{ left: 0, width: "100%" }} content={<ChartLegendContent />} />}
        {chart.series.map((s, i) => (
          <Line
            key={s.key}
            dataKey={s.key}
            type="monotone"
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={lineDot(chart.data.length)}
            connectNulls={false}
            strokeDasharray={LINE_DASHES[i % LINE_DASHES.length]}
            isAnimationActive={!reduced}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
