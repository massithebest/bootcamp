export type KnowledgeKind = "document" | "table" | "kpi" | "recipe" | "glossary" | "simulation";
export type KnowledgeTarget = { kind: KnowledgeKind; id: string; version?: number };
export type KnowledgeStatus = "draft" | "verified";
export interface KnowledgeEntry {
  type: KnowledgeKind; id: string; title: string; summary: string;
  status: KnowledgeStatus; source: string; owner: string; updated: string;
  active: boolean | null; archived: boolean; detail?: Record<string, unknown>;
}
export interface DocumentFields {
  title: string; content: string; category: string; tags: string[]; owner: string; source: string;
}
export interface DocumentVersion extends DocumentFields {
  version: number; status: KnowledgeStatus; created_at: string;
  reviewer: string; review_note: string; reviewed_at: string | null;
}
export interface KnowledgeDocument {
  id: string; revision: number; active_version: number | null; archived: boolean;
  versions: DocumentVersion[];
  history: { revision: number; action: string; version: number | null; actor: string; note: string; at: string }[];
}
export interface KnowledgeTool {
  name: string; description: string; input_schema: Record<string, unknown>; output: string; status: "available";
}
export const KNOWLEDGE_LABELS: Record<KnowledgeKind, string> = {
  document: "텍스트", table: "테이블", kpi: "KPI", recipe: "Recipe", glossary: "용어", simulation: "시뮬레이션",
};
export const STATUS_LABELS = { draft: "미검토", verified: "검토 완료" };
