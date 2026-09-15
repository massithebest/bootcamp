import type { ToolResult } from "@/types/chat";

/** runtime의 isError와 도구 카드가 같은 공개 payload 판정을 사용한다. */
export function toolResultError(result: ToolResult): string | null {
  const data = result.data;
  if (!data) return null;
  if (typeof data.error === "string" && data.error.length > 0) return data.error;
  if (data.status !== "error" && !data.error) return null;
  return typeof data.message === "string" && data.message.length > 0
    ? data.message
    : "도구 실행 중 오류가 발생했습니다.";
}
