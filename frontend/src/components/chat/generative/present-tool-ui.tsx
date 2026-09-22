import { renderGenerativeUI } from "@assistant-ui/react-generative-ui";
import type {
  ToolCallMessagePartComponent,
} from "@assistant-ui/react";

import type { ToolResult } from "@/types/chat";
import { toolResultError } from "@/lib/tool-result";
import { generativeLibrary } from "./library";
import { ResultNotice } from "./message";

/** Python Backend가 검증·실행한 `present` 트리를 공식 renderer로 그린다. */
export const PresentToolUI: ToolCallMessagePartComponent<Record<string, unknown>, ToolResult> = (
  props,
) => {
  const { status, result, isError } = props;
  if (status.type === "running") {
    return <ResultNotice loading>결과 화면을 구성하는 중…</ResultNotice>;
  }
  if (status.type === "incomplete") {
    return (
      <ResultNotice tone={status.reason === "cancelled" ? "neutral" : "alert"}>
        {status.reason === "cancelled" ? "결과 화면 구성이 중단되었습니다." : "결과 화면을 구성하지 못했습니다."}
      </ResultNotice>
    );
  }
  if (status.type === "requires-action") {
    return <ResultNotice>결과 화면을 표시하려면 응답이 필요합니다.</ResultNotice>;
  }
  const error = result ? toolResultError(result) : null;
  if (isError || error) {
    return <ResultNotice tone="alert">{error ?? "결과 화면을 구성하지 못했습니다."}</ResultNotice>;
  }
  return (
    <div data-aui="root">
      {renderGenerativeUI(props.args, generativeLibrary, { status: "done" })}
    </div>
  );
};
