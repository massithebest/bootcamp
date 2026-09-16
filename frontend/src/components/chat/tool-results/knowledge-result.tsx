import { RetrievalChunks } from "@/components/assistant-ui/elements/retrieval-chunks";
import { asRecords, num, str } from "./shared";

/** Existing knowledge payload → official retrieval element; missing scores remain absent. */
export function KnowledgeResult({ data }: { data: Record<string, unknown> }) {
  const chunks = asRecords(data.documents).map((doc, index) => ({
    id: String(index),
    source: str(doc.title) ?? "제목 없음",
    locator: str(doc.section),
    text: str(doc.snippet) ?? str(doc.content),
    score: num(doc.relevance) ?? num(doc.score),
  }));
  return <RetrievalChunks query={str(data.query)} chunks={chunks} />;
}
