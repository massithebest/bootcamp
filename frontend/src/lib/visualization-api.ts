import { API_BASE_URL } from "@/lib/chat-api";
import type {
  ChartSpec,
  VisualizationResponse,
  VisualizationWarning,
} from "@/types/chat";

const ID_PATTERN = /^[0-9a-f]{32}$/;

export type VisualizationErrorKind =
  | "not-found"
  | "unavailable"
  | "network"
  | "invalid-response"
  | "aborted";

export class VisualizationFetchError extends Error {
  constructor(
    public readonly kind: VisualizationErrorKind,
    message: string,
  ) {
    super(message);
    this.name = "VisualizationFetchError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isCategory(value: unknown): value is string | number {
  return (
    typeof value === "string" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

function parseWarnings(value: unknown): VisualizationWarning[] | null {
  if (!Array.isArray(value)) return null;
  const warnings: VisualizationWarning[] = [];
  for (const warning of value) {
    if (
      !isRecord(warning) ||
      typeof warning.code !== "string" ||
      typeof warning.message !== "string"
    ) {
      return null;
    }
    warnings.push({ code: warning.code, message: warning.message });
  }
  return warnings;
}

function parseChart(value: unknown): ChartSpec | null {
  if (!isRecord(value) || (value.type !== "bar" && value.type !== "line")) {
    return null;
  }
  if (
    typeof value.x !== "string" ||
    !Array.isArray(value.series) ||
    value.series.length === 0 ||
    value.series.length > 8 ||
    !Array.isArray(value.categories) ||
    value.categories.length > 500 ||
    !Array.isArray(value.data) ||
    value.data.length !== value.categories.length ||
    !isNullableString(value.title) ||
    !isNullableString(value.x_label) ||
    !isNullableString(value.y_label) ||
    !isNullableString(value.unit)
  ) {
    return null;
  }

  const series: ChartSpec["series"] = [];
  const keys = new Set<string>();
  for (const raw of value.series) {
    if (
      !isRecord(raw) ||
      typeof raw.key !== "string" ||
      !raw.key ||
      keys.has(raw.key) ||
      typeof raw.label !== "string"
    ) {
      return null;
    }
    keys.add(raw.key);
    series.push({ key: raw.key, label: raw.label });
  }

  if (!value.categories.every(isCategory)) return null;
  const data: Record<string, unknown>[] = [];
  for (let index = 0; index < value.data.length; index += 1) {
    const row = value.data[index];
    if (!isRecord(row) || row[value.x] !== value.categories[index]) return null;
    if (Object.keys(row).some((key) => key !== value.x && !keys.has(key))) return null;
    for (const key of keys) {
      const point = row[key];
      if (
        point !== null &&
        !(typeof point === "number" && Number.isFinite(point))
      ) {
        return null;
      }
    }
    data.push(row);
  }

  return {
    type: value.type,
    x: value.x,
    series,
    categories: value.categories,
    data,
    title: value.title,
    x_label: value.x_label,
    y_label: value.y_label,
    unit: value.unit,
  };
}

export function parseVisualizationResponse(
  value: unknown,
): VisualizationResponse | null {
  if (
    !isRecord(value) ||
    typeof value.visualization_id !== "string" ||
    !ID_PATTERN.test(value.visualization_id) ||
    typeof value.result_id !== "string" ||
    !ID_PATTERN.test(value.result_id) ||
    value.schema_version !== 1 ||
    typeof value.expires_at !== "string" ||
    Number.isNaN(Date.parse(value.expires_at))
  ) {
    return null;
  }
  const chart = parseChart(value.chart);
  const warnings = parseWarnings(value.warnings);
  if (!chart || !warnings) return null;
  return {
    visualization_id: value.visualization_id,
    result_id: value.result_id,
    schema_version: 1,
    expires_at: value.expires_at,
    chart,
    warnings,
  };
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export async function fetchVisualization(
  visualizationId: string,
  options: { signal?: AbortSignal } = {},
): Promise<VisualizationResponse> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/api/visualizations/${encodeURIComponent(visualizationId)}`,
      { signal: options.signal, credentials: "include" },
    );
  } catch (error) {
    if (isAbortError(error)) {
      throw new VisualizationFetchError("aborted", "시각화 조회가 취소되었습니다.");
    }
    throw new VisualizationFetchError(
      "network",
      "시각화를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
    );
  }

  if (response.status === 404) {
    throw new VisualizationFetchError(
      "not-found",
      "이 시각화를 조회할 수 없습니다.",
    );
  }
  if (response.status === 410) {
    throw new VisualizationFetchError(
      "unavailable",
      "시각화 원본이 만료되었거나 삭제되었습니다. 새 조회가 필요합니다.",
    );
  }
  if (!response.ok) {
    throw new VisualizationFetchError(
      "network",
      "시각화를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
    );
  }

  let raw: unknown;
  try {
    raw = await response.json();
  } catch {
    throw new VisualizationFetchError(
      "invalid-response",
      "시각화 응답 형식이 올바르지 않습니다.",
    );
  }
  const parsed = parseVisualizationResponse(raw);
  if (!parsed) {
    throw new VisualizationFetchError(
      "invalid-response",
      "시각화 응답 형식이 올바르지 않습니다.",
    );
  }
  return parsed;
}

interface InFlightRequest {
  controller: AbortController;
  promise: Promise<VisualizationResponse>;
  subscribers: number;
  abortTimer: ReturnType<typeof setTimeout> | null;
}

const inFlight = new Map<string, InFlightRequest>();

export function acquireVisualization(visualizationId: string): {
  promise: Promise<VisualizationResponse>;
  release: () => void;
} {
  let request = inFlight.get(visualizationId);
  if (request?.controller.signal.aborted) {
    inFlight.delete(visualizationId);
    request = undefined;
  }
  if (!request) {
    const controller = new AbortController();
    const next: InFlightRequest = {
      controller,
      subscribers: 0,
      abortTimer: null,
      promise: Promise.resolve(null as never),
    };
    next.promise = fetchVisualization(visualizationId, {
      signal: controller.signal,
    }).finally(() => {
      if (inFlight.get(visualizationId) === next) {
        inFlight.delete(visualizationId);
      }
    });
    inFlight.set(visualizationId, next);
    request = next;
  }
  if (request.abortTimer !== null) {
    clearTimeout(request.abortTimer);
    request.abortTimer = null;
  }
  request.subscribers += 1;
  let released = false;
  return {
    promise: request.promise,
    release: () => {
      if (released) return;
      released = true;
      request.subscribers -= 1;
      if (request.subscribers === 0 && inFlight.get(visualizationId) === request) {
        request.abortTimer = setTimeout(() => {
          request.abortTimer = null;
          if (
            request.subscribers === 0 &&
            inFlight.get(visualizationId) === request
          ) {
            request.controller.abort();
          }
        }, 0);
      }
    },
  };
}
