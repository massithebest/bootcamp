/** Adapted from assistant-ui elements/stopped-run; reload restarts the turn, not continuation. */
import { ActionBarPrimitive, useAuiState } from "@assistant-ui/react";
import { RefreshCwIcon, SquareIcon } from "lucide-react";
import { ghostButton } from "./surfaces";

export function StoppedRun() {
  const cancelled = useAuiState((s) => s.message.status?.type === "incomplete" && s.message.status.reason === "cancelled");
  if (!cancelled) return null;
  return (
    <div data-slot="stopped-run" className="flex flex-wrap items-center gap-3 rounded border border-line bg-surface px-3 py-2 text-2xs text-ink-2">
      <span role="status" className="flex items-center gap-2"><SquareIcon aria-hidden className="size-3" />응답 생성을 중단했습니다. 받은 내용은 유지됩니다.</span>
      <ActionBarPrimitive.Reload className={`${ghostButton} inline-flex items-center gap-1.5 px-2 py-1.5 text-2xs`}>
        <RefreshCwIcon aria-hidden className="size-3.5" />다시 실행
      </ActionBarPrimitive.Reload>
    </div>
  );
}
