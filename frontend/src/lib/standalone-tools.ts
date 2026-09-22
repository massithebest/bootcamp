/**
 * 실행 과정 그룹(ToolGroup) 밖에 독립 표면으로 표시하는 Tool 이름.
 * `present_*`는 flat 결과 UI로, 각 Tool이 받은 scalar 인자를 그대로
 * 컴포넌트 prop으로 매핑한다.
 */
export const STANDALONE_TOOL_NAMES: ReadonlySet<string> = new Set([
  "present_sql_preview",
  "present_chart",
  "present_table",
  "present_simulation",
]);

export function isStandaloneTool(toolName: string): boolean {
  return STANDALONE_TOOL_NAMES.has(toolName);
}
