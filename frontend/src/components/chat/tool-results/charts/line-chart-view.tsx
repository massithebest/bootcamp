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
import { LINE_DASHES } from "./chart-style";

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
    <ChartContainer config={config} className="aspect-[16/9] max-h-64 w-full">
      <LineChart data={chart.data} margin={{ left: 12, right: 12, bottom: chart.x_label ? 20 : 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey={chart.x}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          label={
            chart.x_label
              ? { value: chart.x_label, position: "insideBottom", offset: -12 }
              : undefined
          }
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={4}
          width={chart.y_label ? 56 : 40}
          label={
            chart.y_label
              ? { value: chart.y_label, angle: -90, position: "insideLeft" }
              : undefined
          }
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        {(alwaysLegend || chart.series.length > 1) && <ChartLegend content={<ChartLegendContent />} />}
        {chart.series.map((s, i) => (
          <Line
            key={s.key}
            dataKey={s.key}
            type="monotone"
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            strokeDasharray={LINE_DASHES[i % LINE_DASHES.length]}
            isAnimationActive={!reduced}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
