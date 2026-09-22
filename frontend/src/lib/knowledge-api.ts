import { API_BASE_URL } from "./chat-api";
import type { Skill } from "@/types/workspace";
import type {
  ChangeAction, ChangeContent, ChangeDetail, ChangeState, ChangeSummary, DocumentFields, DocumentVersion, FieldData, KindGuide,
  KnowledgeDocument, KnowledgeEntry, KnowledgeKind, KnowledgeTool, Me, StructuredKind, ValidationResult,
} from "@/types/knowledge";
import { getStubUserId } from "./knowledge-user";

type Guard<T> = (value: unknown) => value is T;
const object = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const strings = (v: Record<string, unknown>, keys: string[]) => keys.every(k => typeof v[k] === "string");
const positive = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v > 0;
const status = (v: unknown) => v === "draft" || v === "verified";
const array = <T>(guard: Guard<T>): Guard<T[]> => (v): v is T[] => Array.isArray(v) && v.every(guard);
const skill: Guard<Skill> = (v): v is Skill => object(v) && strings(v, ["name", "description", "status"]);
const entry: Guard<KnowledgeEntry> = (v): v is KnowledgeEntry => object(v) && strings(v, ["id", "title", "summary", "source", "owner", "updated"]) && ["document", "table", "kpi", "recipe", "glossary", "simulation", "scenario"].includes(String(v.type)) && status(v.status) && (v.active === null || typeof v.active === "boolean") && typeof v.archived === "boolean" && (v.pending_change === undefined || v.pending_change === null || (object(v.pending_change) && typeof v.pending_change.id === "string" && ["draft", "submitted", "rejected"].includes(String(v.pending_change.state))));
const version: Guard<DocumentVersion> = (v): v is DocumentVersion => object(v) && strings(v, ["title", "content", "category", "owner", "source", "created_at", "reviewer", "review_note"]) && positive(v.version) && status(v.status) && Array.isArray(v.tags) && v.tags.every(t => typeof t === "string") && (v.reviewed_at === null || typeof v.reviewed_at === "string");
export const isKnowledgeDocument: Guard<KnowledgeDocument> = (v): v is KnowledgeDocument => object(v) && typeof v.id === "string" && positive(v.revision) && (v.active_version === null || positive(v.active_version)) && typeof v.archived === "boolean" && array(version)(v.versions) && v.versions.length > 0 && Array.isArray(v.history) && v.history.every(h => object(h) && positive(h.revision) && strings(h, ["action", "actor", "note", "at"]) && (h.version === null || positive(h.version))) && (v.active_version === null || v.versions.some(r => r.version === v.active_version && r.status === "verified"));
const tool: Guard<KnowledgeTool> = (v): v is KnowledgeTool => object(v) && strings(v, ["name", "description", "output"]) && object(v.input_schema) && v.status === "available";

const CHANGE_STATES = ["draft", "submitted", "approved", "rejected", "withdrawn"];
const summary: Guard<ChangeSummary> = (v): v is ChangeSummary => object(v) && strings(v, ["id", "kind", "key", "created_at", "updated_at"]) && typeof v.is_new === "boolean" && CHANGE_STATES.includes(String(v.state)) && positive(v.revision) && object(v.author) && strings(v.author, ["id", "name"]);
const changeDetail: Guard<ChangeDetail> = (v): v is ChangeDetail => summary(v) && object(v) && strings(v, ["yaml", "current_yaml"]) && object(v.data) && Array.isArray(v.history) && v.history.every(h => object(h) && positive(h.revision) && strings(h, ["action", "actor_id", "actor_name", "note", "at"]) && typeof h.self_approved === "boolean");
const fieldGuide = (v: unknown): boolean => object(v) && strings(v, ["name", "path", "label", "widget"]) && typeof v.required === "boolean" && (v.fields === undefined || (Array.isArray(v.fields) && v.fields.every(fieldGuide)));
const kindGuide: Guard<KindGuide> = (v): v is KindGuide => object(v) && strings(v, ["kind", "key_field"]) && Array.isArray(v.fields) && v.fields.every(fieldGuide) && object(v.template);
const validation: Guard<ValidationResult> = (v): v is ValidationResult => object(v) && typeof v.ok === "boolean" && typeof v.parsed === "boolean" && strings(v, ["yaml", "key"]) && object(v.data) && Array.isArray(v.errors) && v.errors.every(e => object(e) && typeof e.path === "string" && typeof e.message === "string" && (e.line === null || typeof e.line === "number"));
const source: Guard<{ kind: StructuredKind; key: string; yaml: string; data: FieldData }> = (v): v is { kind: StructuredKind; key: string; yaml: string; data: FieldData } => object(v) && strings(v, ["kind", "key", "yaml"]) && object(v.data);
const me: Guard<Me> = (v): v is Me => object(v) && strings(v, ["id", "name"]) && Array.isArray(v.permissions) && v.permissions.every(p => typeof p === "string") && (v.mode === "stub" || v.mode === "authenticated") && typeof v.knowledge_management === "boolean" && typeof v.allow_self_approval === "boolean" && Array.isArray(v.stub_users) && v.stub_users.every(u => object(u) && strings(u, ["id", "name"]));

const ERROR_MESSAGES: Record<number, string> = {
  403: "이 작업을 할 수 없습니다. 권한, 작성자 여부, 자기 승인 제한을 확인하세요.",
  404: "지식 또는 해당 버전을 찾을 수 없습니다.",
  409: "다른 변경이 있거나 현재 상태에서 처리할 수 없습니다. 최신 내용을 다시 불러오세요.",
  422: "필수 입력과 글자 수를 확인하세요.",
};
async function send<T>(path: string, guard: Guard<T>, signal?: AbortSignal, method = "GET", body?: unknown): Promise<T> {
  let response: Response;
  const user = getStubUserId();
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method, signal, headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}), ...(user ? { "X-User-Id": user } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("지식 서버에 연결하지 못했습니다. 다시 시도하세요.");
  }
  if (!response.ok) throw new Error(ERROR_MESSAGES[response.status] ?? "지식 요청을 처리하지 못했습니다. 다시 시도하세요.");
  const data: unknown = await response.json();
  if (!guard(data)) throw new Error("지식 응답 형식을 확인할 수 없습니다.");
  return data;
}
const request = <T,>(path: string, guard: Guard<T>, signal?: AbortSignal, method = "GET", body?: unknown) => send(`/api/knowledge${path}`, guard, signal, method, body);
const id = encodeURIComponent;
export const fetchKnowledgeSkills = (signal?: AbortSignal) => request("/skills", array(skill), signal);
export const fetchKnowledgeSkill = (name: string, signal?: AbortSignal) => request(`/skills/${id(name)}`, (v): v is Skill & { content: string } => skill(v) && object(v) && typeof v.content === "string", signal);
export const fetchKnowledgeTools = (signal?: AbortSignal) => request("/tools", array(tool), signal);
export const fetchKnowledgeEntries = (signal?: AbortSignal, query = "") => request(`/entries?q=${encodeURIComponent(query)}`, array(entry), signal);
export const fetchKnowledgeEntry = (kind: KnowledgeKind, key: string, signal?: AbortSignal) => request(`/entries/${kind}/${id(key)}`, (v): v is KnowledgeEntry => entry(v) && object(v.detail), signal);
export const fetchDocument = (key: string, signal?: AbortSignal) => request(`/documents/${id(key)}`, isKnowledgeDocument, signal);
export const fetchDocumentVersion = (key: string, rev: number, signal?: AbortSignal) => request(`/documents/${id(key)}/versions/${rev}`, version, signal);
export async function saveDocument(fields: DocumentFields, key?: string, revision?: number) {
  const result = await request(key ? `/documents/${id(key)}` : "/documents", isKnowledgeDocument, undefined, key ? "PUT" : "POST", key ? { ...fields, expected_revision: revision } : fields);
  window.dispatchEvent(new Event("knowledge-changed"));
  return result;
}
export async function changeDocument(key: string, action: "review" | "activate" | "deactivate" | "archive", revision: number, actor: string, version?: number, note = "") {
  const result = await request(`/documents/${id(key)}/${action}`, isKnowledgeDocument, undefined, "POST", { expected_revision: revision, actor, version, note });
  window.dispatchEvent(new Event("knowledge-changed"));
  return result;
}

// ---- 구조화 지식 변경 요청 ----
const notify = <T,>(value: T): T => { window.dispatchEvent(new Event("knowledge-changed")); return value; };
export const fetchMe = (signal?: AbortSignal) => send("/api/me", me, signal);
export const fetchKnowledgeGuide = (kind: StructuredKind, signal?: AbortSignal) => request(`/guides/${kind}`, kindGuide, signal);
export const fetchKnowledgeSource = (kind: StructuredKind, key: string, signal?: AbortSignal) => request(`/source/${kind}/${id(key)}`, source, signal);
export const validateKnowledge = (kind: StructuredKind, content: ChangeContent, key?: string, signal?: AbortSignal) => request("/validate", validation, signal, "POST", { kind, ...(key ? { key } : {}), ...content });
export const fetchChanges = (filter: { state?: ChangeState; mine?: boolean } = {}, signal?: AbortSignal) => {
  const query = new URLSearchParams();
  if (filter.state) query.set("state", filter.state);
  if (filter.mine) query.set("mine", "true");
  return request(`/changes${query.size ? `?${query}` : ""}`, array(summary), signal);
};
export const fetchChange = (changeId: string, signal?: AbortSignal) => request(`/changes/${id(changeId)}`, changeDetail, signal);
export const createChange = async (kind: StructuredKind, content: ChangeContent, key?: string) => notify(await request("/changes", changeDetail, undefined, "POST", { kind, ...(key ? { key } : {}), ...content }));
export const updateChange = async (changeId: string, revision: number, content: ChangeContent) => notify(await request(`/changes/${id(changeId)}`, changeDetail, undefined, "PUT", { expected_revision: revision, ...content }));
export const actOnChange = async (changeId: string, action: ChangeAction, revision: number, note = "") => notify(await request(`/changes/${id(changeId)}/${action}`, changeDetail, undefined, "POST", { expected_revision: revision, note }));
