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

/** KPI 카드 숫자. 표와 달리 읽기용이라 천 단위 구분을 붙이고 소수는 최대 2자리까지 보인다. */
export function displayKpiValue(value: string | number): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value);
  return value.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
}

/** 영문 단위(lot, pcs)는 숫자와 띄우고 한글 단위(개, 건)·기호(%)는 붙인다. */
export function kpiUnitSeparator(unit: string): string {
  return /^[A-Za-z]/.test(unit) ? " " : "";
}
