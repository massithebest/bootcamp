import { useEffect, useState } from "react";

import {
  acquireQueryChart,
  acquireQueryTable,
  chartRequestKey,
  QueryResultFetchError,
  tableRequestKey,
} from "@/lib/query-result-api";
import type {
  QueryChartRequest,
  QueryChartResponse,
  QueryTablePage,
  QueryTableRequest,
} from "@/types/query-result";

export type QueryResultState<T> =
  | { type: "loading" }
  | { type: "success"; value: T }
  | { type: "not-found"; message: string }
  | { type: "invalid-request"; message: string; code?: string }
  | { type: "invalid-response"; message: string }
  | { type: "error"; message: string };

function fromError<T>(error: unknown): QueryResultState<T> | null {
  if (error instanceof QueryResultFetchError) {
    if (error.kind === "aborted") return null;
    if (error.kind === "not-found") return { type: "not-found", message: error.message };
    if (error.kind === "invalid-request") {
      return { type: "invalid-request", message: error.message, code: error.code };
    }
    if (error.kind === "invalid-response") {
      return { type: "invalid-response", message: error.message };
    }
    return { type: "error", message: error.message };
  }
  return { type: "error", message: "결과를 불러오지 못했습니다." };
}

function useAcquired<T>(
  key: string,
  retryKey: number,
  acquire: () => { promise: Promise<T>; release: () => void },
): QueryResultState<T> & { stale?: T } {
  const [state, setState] = useState<QueryResultState<T>>({ type: "loading" });
  const [last, setLast] = useState<T | undefined>(undefined);

  useEffect(() => {
    let active = true;
    setState({ type: "loading" });
    const request = acquire();
    request.promise.then(
      (value) => {
        if (!active) return;
        setLast(value);
        setState({ type: "success", value });
      },
      (error: unknown) => {
        if (!active) return;
        const next = fromError<T>(error);
        if (next) setState(next);
      },
    );
    return () => {
      active = false;
      request.release();
    };
    // acquire는 key에서 결정되는 클로저다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, retryKey]);

  return state.type === "loading" ? { ...state, stale: last } : state;
}

export function useQueryChart(request: QueryChartRequest, retryKey: number) {
  return useAcquired<QueryChartResponse>(chartRequestKey(request), retryKey, () =>
    acquireQueryChart(request),
  );
}

/** loading 중에도 직전 page를 `stale`로 돌려 표를 지우지 않는다. */
export function useQueryTable(request: QueryTableRequest, retryKey: number) {
  return useAcquired<QueryTablePage>(tableRequestKey(request), retryKey, () =>
    acquireQueryTable(request),
  );
}
