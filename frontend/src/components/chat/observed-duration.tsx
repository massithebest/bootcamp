import { useEffect, useState } from "react";
import type { ObservedTiming } from "@/types/chat";
import { formatObservedDuration } from "@/lib/execution-summary";

/** Local monotonic time only. Keep ticks outside the live region and message store. */
export function ObservedDuration({ timing, running, label = "대기" }: {
  timing?: ObservedTiming;
  running: boolean;
  label?: string;
}) {
  const [now, setNow] = useState(() => performance.now());
  const startedAt = timing?.startedAt;
  const endedAt = timing?.endedAt;
  useEffect(() => {
    if (startedAt === undefined || endedAt !== undefined || !running) return;
    setNow(performance.now());
    const timer = window.setInterval(() => setNow(performance.now()), 1000);
    return () => window.clearInterval(timer);
  }, [startedAt, endedAt, running]);
  if (startedAt === undefined || (!running && endedAt === undefined)) return null;
  return <span data-slot="observed-duration" className="text-2xs tabular-nums text-ink-2"
    title="응답 시간에는 네트워크 대기가 포함되어 실제 서버 처리 시간과 다를 수 있습니다.">
    {label} {formatObservedDuration((endedAt ?? now) - startedAt)} · 응답 시간
  </span>;
}
