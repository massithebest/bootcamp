/** Y축 눈금은 큰 값만 K/M/B 단위로 줄인다. 툴팁은 원값을 유지한다. */
export function formatYAxisTick(value: number | string): string {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  if (Math.abs(numeric) < 1_000) return String(numeric);

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(numeric);
}
