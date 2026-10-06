import { createRoot } from "react-dom/client";
import { ChartBlock } from "@/components/chat/tool-results/chart-block";
import type { ChartSpec } from "@/types/chat";
import "@/app/globals.css";

const categories = ["202601", "202602", "202603", "202604", "202605", "202606"];
const host = document.querySelector<HTMLElement>("#charts")!;
host.style.width = "680px";
const types = ["bar", "line", "area"] as const;
createRoot(host).render(
  <div className="space-y-4">
    {types.map((type) => {
      const chart: ChartSpec = {
        type, x: "month", series: [
          { key: "fac001", label: "FAC001" }, { key: "fac002", label: "FAC002" }, { key: "fac003", label: "FAC003" },
        ],
        categories,
        data: categories.map((month, index) => ({
          month, fac001: 50000 + index * 2000, fac002: 60000 + index * 3000, fac003: 80000 + index * 4000,
        })),
        title: `${type}: 월별 계획수량`, x_label: "WORK_YM", y_label: "plan_qty_sum", unit: "개",
      };
      return <div key={type} data-chart-type={type}><ChartBlock chart={chart} alwaysLegend stacked={type === "bar"} /></div>;
    })}
  </div>,
);

const results = document.querySelector<HTMLElement>("#results")!;
const deadline = performance.now() + 5000;
function checkAxisSpacing() {
  const ready = types.every((type) => {
    const chart = host.querySelector(`[data-chart-type="${type}"]`);
    const labels = [...(chart?.querySelectorAll("svg text") ?? [])].map((element) => element.textContent);
    return labels.includes("202603") && labels.includes("WORK_YM") && !!chart?.querySelector(".recharts-legend-wrapper");
  });
  if (!ready && performance.now() < deadline) {
    requestAnimationFrame(checkAxisSpacing);
    return;
  }
  const measurements = types.map((type) => {
    const chart = host.querySelector<HTMLElement>(`[data-chart-type="${type}"]`)!;
    const axisText = [...chart.querySelectorAll<SVGTextElement>("svg text")];
    const tick = axisText.find((element) => element.textContent === "202603");
    const title = axisText.find((element) => element.textContent === "WORK_YM");
    const yTitle = axisText.find((element) => element.textContent === "plan_qty_sum");
    const legend = chart.querySelector<HTMLElement>(".recharts-legend-wrapper");
    const svg = chart.querySelector("svg");
    const gridLines = [...chart.querySelectorAll<SVGLineElement>(".recharts-cartesian-grid-horizontal line")];
    const disclosure = chart.querySelector("button");
    const scroller = chart.querySelector<HTMLElement>(".thin-scroll");
    if (!tick || !title || !yTitle || !legend || !svg || !gridLines.length || !disclosure || !scroller) {
      return { type, error: `chart layout elements missing: ${axisText.map((el) => el.textContent)}` };
    }
    const tickGap = title.getBoundingClientRect().top - tick.getBoundingClientRect().bottom;
    const legendGap = legend.getBoundingClientRect().top - title.getBoundingClientRect().bottom;
    const svgRect = svg.getBoundingClientRect();
    const legendRect = legend.getBoundingClientRect();
    const gridTop = Math.min(...gridLines.map((line) => Number(line.getAttribute("y1"))));
    const gridBottom = Math.max(...gridLines.map((line) => Number(line.getAttribute("y1"))));
    const plotCenterX = svgRect.left + (Number(gridLines[0].getAttribute("x1")) + Number(gridLines[0].getAttribute("x2"))) / 2;
    const plotCenterY = svgRect.top + (gridTop + gridBottom) / 2;
    const yRect = yTitle.getBoundingClientRect();
    const xOffset = plotCenterX - (svgRect.left + svgRect.width / 2);
    const yOffset = (yRect.top + yRect.height / 2) - plotCenterY;
    const legendOffset = (legendRect.left + legendRect.width / 2) - plotCenterX;
    const disclosureGap = disclosure.getBoundingClientRect().top - legendRect.bottom;
    const overflow = scroller.scrollWidth - scroller.clientWidth;
    return {
      type, tickGap, legendGap, xOffset, yOffset, legendOffset, disclosureGap, overflow,
      pass: tickGap >= 8 && legendGap >= 4 && Math.abs(xOffset) <= 2 && Math.abs(yOffset) <= 2
        && Math.abs(legendOffset) <= 2 && disclosureGap >= 8 && disclosureGap <= 28 && overflow === 0,
    };
  });
  results.textContent = JSON.stringify(measurements, null, 2);
  document.title = measurements.every((measurement) => "pass" in measurement && measurement.pass) ? "PASS" : "FAIL";
}
requestAnimationFrame(checkAxisSpacing);
