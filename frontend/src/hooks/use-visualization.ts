import { useEffect, useState } from "react";

import {
  acquireVisualization,
  VisualizationFetchError,
} from "@/lib/visualization-api";
import type { VisualizationResponse } from "@/types/chat";

export type VisualizationState =
  | { type: "loading" }
  | { type: "success"; response: VisualizationResponse }
  | { type: "not-found"; message: string }
  | { type: "unavailable"; message: string }
  | { type: "error"; message: string };

export function useVisualization(
  visualizationId: string,
  retryKey: number,
): VisualizationState {
  const [state, setState] = useState<VisualizationState>({ type: "loading" });

  useEffect(() => {
    let active = true;
    setState({ type: "loading" });
    const request = acquireVisualization(visualizationId);
    request.promise.then(
      (response) => {
        if (active) setState({ type: "success", response });
      },
      (error: unknown) => {
        if (!active) return;
        if (error instanceof VisualizationFetchError) {
          if (error.kind === "aborted") return;
          if (error.kind === "not-found") {
            setState({ type: "not-found", message: error.message });
            return;
          }
          if (error.kind === "unavailable") {
            setState({ type: "unavailable", message: error.message });
            return;
          }
          setState({ type: "error", message: error.message });
          return;
        }
        setState({ type: "error", message: "시각화를 불러오지 못했습니다." });
      },
    );
    return () => {
      active = false;
      request.release();
    };
  }, [visualizationId, retryKey]);

  return state;
}
