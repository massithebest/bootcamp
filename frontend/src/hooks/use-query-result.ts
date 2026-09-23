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
  const [result, setResult] = useState<{
    key: string;
    retryKey: number;
    state: QueryResultState<T>;
    last?: { key: string; value: T };
  }>(() => ({ key, retryKey, state: { type: "loading" } }));

  useEffect(() => {
    let active = true;
    setResult((current) => ({
      key,
      retryKey,
      state: { type: "loading" },
      last: current.last?.key === key ? current.last : undefined,
    }));
    const request = acquire();
    request.promise.then(
      (value) => {
        if (!active) return;
        setResult({
          key,
          retryKey,
          state: { type: "success", value },
          last: { key, value },
        });
      },
      (error: unknown) => {
        if (!active) return;
        const next = fromError<T>(error);
        if (next) {
          setResult((current) => ({
            key,
            retryKey,
            state: next,
            last: current.last?.key === key ? current.last : undefined,
          }));
        }
      },
    );
    return () => {
      active = false;
      request.release();
    };
    // acquire는 key에서 결정되는 클로저다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, retryKey]);

  const matchesRequest = result.key === key && result.retryKey === retryKey;
  if (!matchesRequest) {
    const stale = result.last?.key === key ? result.last.value : undefined;
    return stale === undefined ? { type: "loading" } : { type: "loading", stale };
  }
  if (result.state.type === "loading" && result.last?.key === key) {
    return { ...result.state, stale: result.last.value };
  }
  return result.state;
}

export function useQueryChart(request: QueryChartRequest, retryKey: number) {
  return useAcquired<QueryChartResponse>(chartRequestKey(request), retryKey, () =>
    acquireQueryChart(request),
  );
}

/** 같은 요청을 재시도하는 동안에만 이전 page를 `stale`로 유지한다. */
export function useQueryTable(request: QueryTableRequest, retryKey: number) {
  return useAcquired<QueryTablePage>(tableRequestKey(request), retryKey, () =>
    acquireQueryTable(request),
  );
}
