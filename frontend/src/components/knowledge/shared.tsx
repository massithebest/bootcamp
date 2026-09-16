import type { KnowledgeEntry } from "@/types/knowledge";
import { STATUS_LABELS } from "@/types/knowledge";

export const controlClass = "w-full rounded border border-line-strong bg-canvas px-2.5 py-2 text-ui text-ink focus:outline-none focus:ring-2 focus:ring-accent";
export const buttonClass = "rounded border border-line-strong px-3 py-1.5 text-ui text-ink hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50";
export function ResourceState({ loading, error, retry }: { loading: boolean; error?: string; retry: () => void }) {
  if (loading) return <p role="status" className="py-3 text-ui text-ink-3">불러오는 중…</p>;
  if (error) return <div role="alert" className="my-2 border-l-2 border-warn-ink bg-warn-weak p-3 text-ui"><p>{error}</p><button className={`${buttonClass} mt-2`} onClick={retry}>다시 불러오기</button></div>;
  return null;
}
export function EntryStatus({ entry }: { entry: Pick<KnowledgeEntry, "status" | "active" | "archived"> }) {
  return <span className="flex flex-wrap gap-1.5 text-2xs"><span className={entry.status === "verified" ? "text-ok-ink" : "text-warn-ink"}>{STATUS_LABELS[entry.status]}</span>{entry.active !== null && <span className={entry.active ? "text-ok-ink" : "text-ink-3"}>{entry.archived ? "보관됨" : entry.active ? "검색 반영 중" : "검색 제외"}</span>}</span>;
}
