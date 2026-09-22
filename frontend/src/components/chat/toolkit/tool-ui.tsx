import type { ToolCallMessagePartComponent } from "@assistant-ui/react";
import { useAuiState } from "@assistant-ui/react";

import { readAgentMetadata } from "@/lib/chat-runtime";
import type { ToolResult } from "@/types/chat";
import { ToolResultCard } from "../tool-result-card";

/**
 * 실행 과정 그룹 안에서 Tool 하나의 파라미터·결과를 두 번째 disclosure로 보여 준다.
 * toolkit에 도구별로 등록해 쓰고, 등록되지 않은 도구의 fallback으로도 쓴다.
 * 종류별 본문(SQL·문서·simulation·catalog)은 `ToolResultCard`가 결과 kind로 고른다.
 */
export const RegisteredToolUI: ToolCallMessagePartComponent<Record<string, unknown>, ToolResult> = (props) => {
  const result = props.result as ToolResult | undefined;
  const args = isRecord(props.args) ? props.args : {};
  const messageRunning = useAuiState((s) => s.message.status?.type === "running");
  const metadata = useAuiState((s) => s.message.metadata.custom);

  return (
    <ToolResultCard
      toolName={props.toolName}
      args={args}
      result={result}
      running={props.status.type === "running"}
      messageRunning={messageRunning}
      observedTiming={readAgentMetadata(metadata)?.toolTimings?.[props.toolCallId]}
    />
  );
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
