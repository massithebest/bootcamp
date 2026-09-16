import { RetrievalChunks } from "@/components/assistant-ui/elements/retrieval-chunks";
import { useKnowledgeNavigation } from "@/components/knowledge/navigation";
import { asRecords, num, str } from "./shared";

/** Existing knowledge payload → official retrieval element; missing scores remain absent. */
export function KnowledgeResult({ data }: { data: Record<string, unknown> }) {
  const open = useKnowledgeNavigation();
  const documents = asRecords(data.documents);
  const chunks = asRecords(data.documents).map((doc, index) => ({
    id: String(index),
    source: str(doc.title) ?? "제목 없음",
    locator: str(doc.section),
    text: str(doc.snippet) ?? str(doc.content),
    score: num(doc.relevance) ?? num(doc.score),
  }));
  return <div className="space-y-2"><RetrievalChunks query={str(data.query)} chunks={chunks} />
    {documents.length === 0 && <p className="text-ui text-ink-3">{str(data.message) ?? "관련 근거를 찾지 못했습니다."}</p>}
    {documents.map((doc, index) => typeof doc.document_id === "string" && typeof doc.version === "number" && Number.isInteger(doc.version) && doc.version > 0 ? <div key={`${doc.document_id}:${doc.version}`} className="text-2xs text-ink-2"><span>{str(doc.source) ?? "출처 미기록"} · {doc.verified === true ? "검토 완료" : "미검증"} · </span><button className="text-accent hover:underline" onClick={() => open({ kind: "document", id: String(doc.document_id), version: Number(doc.version) })}>{str(doc.title) ?? `문서 ${index + 1}`} v{doc.version} 원문 보기</button></div> : null)}
  </div>;
}
