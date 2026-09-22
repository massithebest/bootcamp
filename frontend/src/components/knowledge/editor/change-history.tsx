import { formatTime } from "@/lib/format-time";
import { CHANGE_ACTION_LABELS, type ChangeHistoryItem } from "@/types/knowledge";

/** 요청의 진행 이력. 승인·반려 근거와 자기 승인 여부를 감사 목적으로 그대로 보여준다. */
export function ChangeHistory({ items }: { items: ChangeHistoryItem[] }) {
  return <ol className="space-y-3">{items.map(item => <li key={item.revision} className="border-l-2 border-line pl-3">
    <p className="text-ui text-ink"><span className="font-semibold">{CHANGE_ACTION_LABELS[item.action] ?? item.action}</span><span className="text-ink-2"> · {item.actor_name}</span>{item.self_approved && <span className="ml-2 text-2xs text-warn-ink">작성자 본인 승인</span>}</p>
    <p className="text-2xs tabular-nums text-ink-3">{formatTime(item.at)}</p>
    {item.note && <p className="mt-1 whitespace-pre-wrap break-words text-ui text-ink-2">{item.note}</p>}
  </li>)}</ol>;
}
