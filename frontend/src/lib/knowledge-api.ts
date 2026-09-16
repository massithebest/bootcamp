import { API_BASE_URL } from "./chat-api";
import type { Skill } from "@/types/workspace";
import type { DocumentFields, DocumentVersion, KnowledgeDocument, KnowledgeEntry, KnowledgeKind, KnowledgeTool } from "@/types/knowledge";

type Guard<T> = (value: unknown) => value is T;
const object = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const strings = (v: Record<string, unknown>, keys: string[]) => keys.every(k => typeof v[k] === "string");
const positive = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v > 0;
const status = (v: unknown) => v === "draft" || v === "verified";
const array = <T>(guard: Guard<T>): Guard<T[]> => (v): v is T[] => Array.isArray(v) && v.every(guard);
const skill: Guard<Skill> = (v): v is Skill => object(v) && strings(v, ["name", "description", "status"]);
const entry: Guard<KnowledgeEntry> = (v): v is KnowledgeEntry => object(v) && strings(v, ["id", "title", "summary", "source", "owner", "updated"]) && ["document", "table", "kpi", "recipe", "glossary", "simulation"].includes(String(v.type)) && status(v.status) && (v.active === null || typeof v.active === "boolean") && typeof v.archived === "boolean";
const version: Guard<DocumentVersion> = (v): v is DocumentVersion => object(v) && strings(v, ["title", "content", "category", "owner", "source", "created_at", "reviewer", "review_note"]) && positive(v.version) && status(v.status) && Array.isArray(v.tags) && v.tags.every(t => typeof t === "string") && (v.reviewed_at === null || typeof v.reviewed_at === "string");
export const isKnowledgeDocument: Guard<KnowledgeDocument> = (v): v is KnowledgeDocument => object(v) && typeof v.id === "string" && positive(v.revision) && (v.active_version === null || positive(v.active_version)) && typeof v.archived === "boolean" && array(version)(v.versions) && v.versions.length > 0 && Array.isArray(v.history) && v.history.every(h => object(h) && positive(h.revision) && strings(h, ["action", "actor", "note", "at"]) && (h.version === null || positive(h.version))) && (v.active_version === null || v.versions.some(r => r.version === v.active_version && r.status === "verified"));
const tool: Guard<KnowledgeTool> = (v): v is KnowledgeTool => object(v) && strings(v, ["name", "description", "output"]) && object(v.input_schema) && v.status === "available";

async function request<T>(path: string, guard: Guard<T>, signal?: AbortSignal, method = "GET", body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/knowledge${path}`, {
      method, signal, headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("지식 서버에 연결하지 못했습니다. 다시 시도하세요.");
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      404: "지식 또는 해당 버전을 찾을 수 없습니다.",
      409: "다른 변경이 있거나 현재 상태에서 처리할 수 없습니다. 최신 내용을 다시 불러오세요.",
      422: "필수 입력과 글자 수를 확인하세요.",
    };
    throw new Error(messages[response.status] ?? "지식 요청을 처리하지 못했습니다. 다시 시도하세요.");
  }
  const data: unknown = await response.json();
  if (!guard(data)) throw new Error("지식 응답 형식을 확인할 수 없습니다.");
  return data;
}
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
