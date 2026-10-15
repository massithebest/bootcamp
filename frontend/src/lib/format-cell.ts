/** 표 셀 표시 규칙. 숫자·문자는 그대로, NULL은 대시, 불리언은 true/false. */
export type DisplayCell = string | number | boolean | null | undefined;

/** 부동소수점 집계 오차(13083.199999999999)를 걷어낸 숫자 문자열. 천 단위 구분은 붙이지 않는다. */
const NUMBER_PRECISION = 12;

export function displayCell(value: DisplayCell): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number" && Number.isFinite(value) && !Number.isInteger(value)) {
    return String(Number(value.toPrecision(NUMBER_PRECISION)));
  }
  return String(value);
}
