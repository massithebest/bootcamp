/** Turn termination is not proof that every tool succeeded. */
export function executionSummary(parts: readonly {
  type: string; result?: unknown; isError?: boolean;
}[], running: boolean) {
  const tools = parts.filter((part) => part.type === "tool-call");
  const errors = tools.filter((part) => part.isError).length;
  const pending = tools.filter((part) => part.result === undefined).length;
  const incomplete = running ? 0 : pending;
  const issues = [errors ? `오류 ${errors}개` : "", incomplete ? `미완료 ${incomplete}개` : ""].filter(Boolean).join(" · ");
  return { count: tools.length, errors, pending, incomplete, issues };
}

export function formatObservedDuration(milliseconds: number): string {
  const seconds = Math.floor(Math.max(0, milliseconds) / 1000);
  return seconds < 1 ? "1초 미만" : seconds < 60 ? `${seconds}초` : `${Math.floor(seconds / 60)}분 ${seconds % 60}초`;
}
