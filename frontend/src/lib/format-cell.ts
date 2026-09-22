/** 표 셀 표시 규칙. 숫자·문자는 그대로, NULL은 대시, 불리언은 true/false. */
export type DisplayCell = string | number | boolean | null | undefined;

export function displayCell(value: DisplayCell): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}
