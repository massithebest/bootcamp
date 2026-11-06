import type { KnowledgeEntry } from "@/types/knowledge";

/** 검토 대기 목록의 미검토 지식. 보관된 지식과, 제출된 변경 요청으로 이미 목록에 있는 지식은 뺀다. */
export const unreviewedEntries = (entries: KnowledgeEntry[]): KnowledgeEntry[] =>
  entries.filter(entry => entry.status === "draft" && !entry.archived && entry.pending_change?.state !== "submitted");
