export type StructuredKind = "table" | "kpi" | "recipe" | "glossary" | "simulation" | "scenario";
export type KnowledgeKind = "document" | StructuredKind;
export type KnowledgeTarget = { kind: KnowledgeKind; id: string; version?: number };
export type KnowledgeStatus = "draft" | "verified";
export interface KnowledgeEntry {
  type: KnowledgeKind; id: string; title: string; summary: string;
  status: KnowledgeStatus; source: string; owner: string; updated: string;
  active: boolean | null; archived: boolean; detail?: Record<string, unknown>;
  /** 진행 중인 구조화 지식 변경 요청. 텍스트 지식에는 없다. */
  pending_change?: { id: string; state: OpenChangeState } | null;
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
  document: "텍스트", table: "테이블", kpi: "KPI", recipe: "Recipe", glossary: "용어", simulation: "시뮬레이션", scenario: "시나리오",
};
export const STRUCTURED_KINDS = ["table", "kpi", "recipe", "simulation", "glossary", "scenario"] as const satisfies readonly StructuredKind[];
export const STATUS_LABELS = { draft: "미검토", verified: "검토 완료" };

// ---- 구조화 지식 변경 요청 ----
export type ChangeState = "draft" | "submitted" | "approved" | "rejected" | "withdrawn";
export type OpenChangeState = "draft" | "submitted" | "rejected";
export type ChangeAction = "submit" | "withdraw" | "approve" | "reject";
export const CHANGE_STATE_LABELS: Record<ChangeState, string> = {
  draft: "초안", submitted: "검토 대기", approved: "승인됨", rejected: "반려됨", withdrawn: "철회됨",
};
export const CHANGE_ACTION_LABELS: Record<ChangeAction | "create" | "save", string> = {
  create: "요청 생성", save: "초안 저장", submit: "검토 요청", withdraw: "요청 철회", approve: "승인", reject: "반려",
};
export interface ChangeSummary {
  id: string; kind: StructuredKind; key: string; is_new: boolean; state: ChangeState; revision: number;
  author: { id: string; name: string }; created_at: string; updated_at: string;
}
export interface ChangeHistoryItem {
  revision: number; action: ChangeAction | "create" | "save"; actor_id: string; actor_name: string;
  note: string; self_approved: boolean; at: string;
}
export interface ChangeDetail extends ChangeSummary {
  yaml: string; data: Record<string, unknown>; current_yaml: string; history: ChangeHistoryItem[];
}
export type FieldData = Record<string, unknown>;
export type FieldWidget = "string" | "text" | "sql" | "boolean" | "number" | "date" | "enum" | "string_list" | "record_list" | "object" | "map" | "json";
/** 백엔드 `GET /api/knowledge/guides/{kind}`의 필드 명세. 구조는 모델, 문구는 가이드가 소유한다. */
export interface FieldGuide {
  name: string; path: string; label: string; help: string; required: boolean; readonly: boolean;
  widget: FieldWidget; example?: string; group?: string;
  options?: string[]; item_widget?: "string" | "text";
  fields?: FieldGuide[]; value?: { widget: FieldWidget; fields?: FieldGuide[] };
}
export interface KindGuide { kind: StructuredKind; key_field: string; fields: FieldGuide[]; template: FieldData; immutable: string[] }
export interface ValidationError { path: string; line: number | null; message: string }
export interface ValidationResult { ok: boolean; parsed: boolean; yaml: string; data: FieldData; key: string; errors: ValidationError[] }
export type ChangeContent = { yaml: string; data?: undefined } | { data: FieldData; yaml?: undefined };
export interface Me {
  id: string; name: string; permissions: string[]; mode: "stub" | "authenticated";
  knowledge_management: boolean; allow_self_approval: boolean; stub_users: { id: string; name: string }[];
}
export const PERMISSION_WRITE = "knowledge:write";
export const PERMISSION_APPROVE = "knowledge:approve";
