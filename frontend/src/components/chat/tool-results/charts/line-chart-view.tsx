import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { ChartSpec } from "@/types/chat";

const PALETTE = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function LineChartView({ chart }: { chart: ChartSpec }) {
  const config: ChartConfig = Object.fromEntries(
    chart.series.map((s, i) => [
      s.key,
      { label: s.label, color: PALETTE[i % PALETTE.length] },
    ]),
  );

  return (
    <ChartContainer config={config} className="aspect-[16/9] max-h-64 w-full">
      <LineChart data={chart.data} margin={{ left: 4, right: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey={chart.x}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
        />
        <YAxis tickLine={false} axisLine={false} tickMargin={4} width={40} />
        <ChartTooltip content={<ChartTooltipContent />} />
        {chart.series.length > 1 && <ChartLegend content={<ChartLegendContent />} />}
        {chart.series.map((s, i) => (
          <Line
            key={s.key}
            dataKey={s.key}
            type="monotone"
            stroke={PALETTE[i % PALETTE.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}
