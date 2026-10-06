import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
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

const PALETTE = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function BarChartView({
  chart,
  alwaysLegend = false,
  stacked = false,
}: {
  chart: ChartSpec;
  alwaysLegend?: boolean;
  stacked?: boolean;
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
      <BarChart data={chart.data} margin={{ left: 12, right: 12, bottom: chart.x_label ? 20 : 0 }}>
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
          <Bar
            key={s.key}
            dataKey={s.key}
            stackId={stacked ? "bar-stack" : undefined}
            fill={PALETTE[i % PALETTE.length]}
            radius={2}
            isAnimationActive={!reduced}
          />
        ))}
      </BarChart>
    </ChartContainer>
  );
}
