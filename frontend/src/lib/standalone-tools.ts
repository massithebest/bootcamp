/**
 * 실행 과정 그룹(ToolGroup) 밖에 독립 표면으로 표시하는 Tool 이름.
 * `prepare_*`는 legacy 결과 UI(과거 메시지와 `RESULT_UI_MODE=legacy`), `present_*`는
 * flat 결과 UI(`RESULT_UI_MODE=present`)다.
 */
export const STANDALONE_TOOL_NAMES: ReadonlySet<string> = new Set([
  "prepare_table",
  "prepare_visualization",
  "present_sql_preview",
  "present_chart",
  "present_table",
  "present_simulation",
]);

export function isStandaloneTool(toolName: string): boolean {
  return STANDALONE_TOOL_NAMES.has(toolName);
}
