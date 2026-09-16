import { useState } from "react";
import { useAuiState } from "@assistant-ui/react";

import { useVisualization } from "@/hooks/use-visualization";
import {
  parseChartMarker,
  visualizationIdFromToolResult,
} from "@/lib/chart-marker";
import { ChartBlock } from "./chart-block";

export function ChartMarker({ source }: { source: string }) {
  const parsed = parseChartMarker(source);
  const messageStatus = useAuiState((state) => state.message.status?.type);
  const alreadyRenderedByToolUi = useAuiState((state) => {
    if (parsed.type !== "valid") return false;
    return state.message.parts.some(
      (part) =>
        part.type === "tool-call" &&
        part.toolName === "prepare_visualization" &&
        visualizationIdFromToolResult(part.result) === parsed.visualizationId,
    );
  });

  if (parsed.type === "incomplete") {
    return messageStatus === "running" ? (
      <ChartMarkerLoading />
    ) : (
      <ChartMarkerMessage message="차트 마커가 완성되지 않았습니다." alert />
    );
  }
  if (parsed.type === "invalid") {
    return <ChartMarkerMessage message="올바르지 않은 차트 마커입니다." alert />;
  }
  if (alreadyRenderedByToolUi) return null;
  return <VisualizationById visualizationId={parsed.visualizationId} />;
}

/** Tool UI와 과거 chart marker가 공유하는 검증된 ID 기반 조회 renderer. */
export function VisualizationById({ visualizationId }: { visualizationId: string }) {
  const [retryKey, setRetryKey] = useState(0);
  const state = useVisualization(visualizationId, retryKey);

  if (state.type === "loading") return <ChartMarkerLoading />;
  if (state.type === "success") {
    return (
      <ChartBlock
        chart={state.response.chart}
        warnings={state.response.warnings}
      />
    );
  }
  if (state.type === "error") {
    return (
      <div className="rounded border border-line bg-surface px-3 py-2" role="alert">
        <p className="text-ui text-ink-2">{state.message}</p>
        <button
          type="button"
          className="mt-2 rounded border border-line-strong px-2 py-1 text-2xs text-ink-2 hover:bg-surface-2"
          onClick={() => setRetryKey((value) => value + 1)}
        >
          다시 시도
        </button>
      </div>
    );
  }
  return <ChartMarkerMessage message={state.message} alert />;
}

function ChartMarkerLoading() {
  return (
    <div
      className="h-48 animate-pulse rounded border border-line bg-surface-2"
      role="status"
      aria-label="차트를 불러오는 중"
    />
  );
}

function ChartMarkerMessage({ message, alert = false }: { message: string; alert?: boolean }) {
  return (
    <p
      className="rounded border border-line bg-surface px-3 py-2 text-ui text-ink-2"
      role={alert ? "alert" : "status"}
    >
      {message} 표가 있으면 확인하고, 없으면 새 조회를 요청해 주세요.
    </p>
  );
}
