import type { ToolCallMessagePartComponent } from "@assistant-ui/react";

import type { ToolResult } from "@/types/chat";
import { visualizationIdFromToolResult } from "@/lib/chart-marker";
import { toolResultError } from "@/lib/tool-result";
import { VisualizationById } from "./chart-marker";

type VisualizationArgs = {
  result_id?: unknown;
  kind?: unknown;
  x?: unknown;
  y?: unknown;
  group_by?: unknown;
};

/** Python Backend에서 실행되는 prepare_visualization의 렌더링 전용 Tool UI. */
export const VisualizationToolUI: ToolCallMessagePartComponent<
  VisualizationArgs,
  ToolResult
> = ({ status, result, isError }) => {
  if (status.type === "running") {
    return <VisualizationToolMessage message="차트를 준비하고 있습니다." loading />;
  }

  if (status.type === "incomplete") {
    return (
      <VisualizationToolMessage
        message={
          status.reason === "cancelled"
            ? "차트 준비가 중단되었습니다."
            : "차트를 준비하지 못했습니다."
        }
        alert={status.reason !== "cancelled"}
      />
    );
  }

  if (status.type === "requires-action") {
    return <VisualizationToolMessage message="차트 준비를 계속하려면 응답이 필요합니다." />;
  }

  const error = result ? toolResultError(result) : null;
  if (isError || error) {
    return <VisualizationToolMessage message={error ?? "차트를 준비하지 못했습니다."} alert />;
  }

  const visualizationId = visualizationIdFromToolResult(result);
  if (!visualizationId) {
    return <VisualizationToolMessage message="유효한 차트 결과를 받지 못했습니다." alert />;
  }

  return <VisualizationById visualizationId={visualizationId} />;
};

function VisualizationToolMessage({
  message,
  alert = false,
  loading = false,
}: {
  message: string;
  alert?: boolean;
  loading?: boolean;
}) {
  return (
    <div
      className="flex min-h-24 items-center justify-center rounded border border-line bg-surface-2 px-4 text-ui text-ink-2"
      role={alert ? "alert" : "status"}
      aria-busy={loading || undefined}
    >
      <span className={loading ? "shimmer motion-reduce:animate-none" : undefined}>{message}</span>
    </div>
  );
}
