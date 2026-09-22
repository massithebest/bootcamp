import { CHANGE_STATE_LABELS, type ChangeState } from "@/types/knowledge";

const TONE: Record<ChangeState, string> = {
  draft: "text-ink-2", submitted: "text-warn-ink", approved: "text-ok-ink", rejected: "text-block-ink", withdrawn: "text-ink-3",
};

/** 색만으로 전달하지 않도록 점과 텍스트를 함께 쓴다. */
export function ChangeStateBadge({ state }: { state: ChangeState }) {
  return <span className={`inline-flex items-center gap-1.5 text-2xs font-medium ${TONE[state]}`}><span aria-hidden className="size-1.5 rounded-full bg-current" />{CHANGE_STATE_LABELS[state]}</span>;
}
