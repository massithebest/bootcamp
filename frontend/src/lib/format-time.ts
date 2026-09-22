/** 서버가 보낸 UTC ISO 시각을 사용자 로컬 시각의 짧은 표기로 바꾼다. 해석할 수 없으면 원문을 그대로 돌려준다. */
const formatter = new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
export function formatTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : formatter.format(date);
}
