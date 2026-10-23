import type { ReactNode } from "react";
import { displayKpiValue, kpiUnitSeparator } from "@/lib/format-cell";

export interface SimulationSummaryProps {
  scenario: string;
  summary: string;
  kpis: { label: string; value: string | number; unit?: string }[];
  resultId?: string;
  children?: ReactNode;
}

/** 시나리오·요약·KPI를 보여 준다. 값은 서버가 준 그대로 쓰고 숫자 표기(천 단위 구분)만 바꾼다. */
export function SimulationSummary({ scenario, summary, kpis, children }: SimulationSummaryProps) {
  return (
    <section
      data-slot="simulation-summary"
      aria-label={scenario}
      className="flex min-w-0 flex-col gap-3"
    >
      <p className="font-mono text-2xs text-ink-3">{scenario}</p>
      {kpis.length > 0 && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          {kpis.map((kpi, index) => (
            <div key={`${kpi.label}:${index}`} className="flex flex-col gap-1">
              <dt className="text-2xs text-ink-3">{kpi.label}</dt>
              <dd className="font-mono text-ui-lg font-medium tabular-nums text-ink">
                {displayKpiValue(kpi.value)}
                {kpi.unit && (
                  <span className="ml-0.5 text-2xs font-normal text-ink-3">
                    {kpiUnitSeparator(kpi.unit)}
                    {kpi.unit}
                  </span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p className="text-ui leading-relaxed text-ink-2">{summary}</p>
      {children && <div className="flex flex-col gap-3">{children}</div>}
    </section>
  );
}
