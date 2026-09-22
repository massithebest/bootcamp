import type { ValidationError } from "@/types/knowledge";

/** 저장 전 검증 결과. 통과·진행·오류를 점과 문장으로 함께 알리고 변경은 polite live region 으로 전달한다. */
export function ValidationSummary({ errors, ok, checking, unavailable }: { errors: ValidationError[]; ok: boolean; checking: boolean; unavailable?: string }) {
  let body;
  if (unavailable) body = <p className="text-ui text-warn-ink">{unavailable}</p>;
  else if (checking) body = <p className="text-ui text-ink-3">검증 중…</p>;
  else if (ok) body = <p className="flex items-center gap-1.5 text-ui text-ok-ink"><span aria-hidden className="size-1.5 rounded-full bg-current" />검증을 통과했습니다. 검토를 요청할 수 있습니다.</p>;
  else if (errors.length) body = <div className="space-y-1.5">
    <p className="flex items-center gap-1.5 text-ui font-semibold text-block-ink"><span aria-hidden className="size-1.5 rounded-full bg-current" />확인이 필요한 항목 {errors.length}개</p>
    <ul className="space-y-1 text-ui text-ink">{errors.map((error, index) => <li key={index} className="flex gap-2"><code className="shrink-0 font-mono text-data text-ink-2">{error.line ? `${error.line}행` : error.path || "전체"}</code><span className="min-w-0 break-words">{error.message}</span></li>)}</ul>
  </div>;
  return <div aria-live="polite" className="min-h-6 border-l-2 border-line pl-3">{body}</div>;
}
