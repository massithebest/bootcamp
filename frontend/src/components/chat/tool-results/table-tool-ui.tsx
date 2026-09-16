import type { ToolCallMessagePartComponent } from "@assistant-ui/react";

import type { ToolResult } from "@/types/chat";
import { tablePayloadFromToolResult } from "@/lib/table-tool";
import { toolResultError } from "@/lib/tool-result";
import { InteractiveDataTable } from "./interactive-data-table";

type TableArgs = {
  result_id?: unknown;
  columns?: unknown;
  title?: unknown;
};

/** Python Backend에서 실행되는 prepare_table의 렌더링 전용 Tool UI. */
export const TableToolUI: ToolCallMessagePartComponent<TableArgs, ToolResult> = ({
  status,
  result,
  isError,
}) => {
  if (status.type === "running") {
    return <TableToolMessage message="표를 준비하고 있습니다." loading />;
  }
  if (status.type === "incomplete") {
    return (
      <TableToolMessage
        message={status.reason === "cancelled" ? "표 준비가 중단되었습니다." : "표를 준비하지 못했습니다."}
        alert={status.reason !== "cancelled"}
      />
    );
  }
  if (status.type === "requires-action") {
    return <TableToolMessage message="표 준비를 계속하려면 응답이 필요합니다." />;
  }

  const error = result ? toolResultError(result) : null;
  if (isError || error) {
    return <TableToolMessage message={error ?? "표를 준비하지 못했습니다."} alert />;
  }

  const table = tablePayloadFromToolResult(result);
  if (!table) {
    return <TableToolMessage message="유효한 표 결과를 받지 못했습니다." alert />;
  }
  return <InteractiveDataTable table={table} />;
};

function TableToolMessage({
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
      role={alert ? "alert" : undefined}
      aria-busy={loading || undefined}
    >
      <span className={loading ? "shimmer motion-reduce:animate-none" : undefined}>{message}</span>
    </div>
  );
}
