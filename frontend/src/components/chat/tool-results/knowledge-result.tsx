import { asRecords, num, str } from "./shared";

/** 문서 검색 결과 → 출처 문서명 · 관련도 · 스니펫 인용 형태. */
export function KnowledgeResult({ data }: { data: Record<string, unknown> }) {
  const query = str(data.query);
  const documents = asRecords(data.documents);
  if (documents.length === 0) return null;

  return (
    <div className="flex flex-col gap-2.5">
      {query && (
        <p className="text-2xs text-ink-3">
          검색어 <span className="font-mono text-ink-2">{query}</span>
        </p>
      )}
      <ul className="flex flex-col gap-2.5">
        {documents.map((doc, i) => {
          const title = str(doc.title) ?? "제목 없음";
          const section = str(doc.section);
          const snippet = str(doc.snippet);
          const relevance = num(doc.relevance);
          return (
            <li
              key={i}
              className="border-l-2 border-line-strong pl-3"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-ui font-medium text-ink">{title}</span>
                {relevance !== null && (
                  <span className="shrink-0 font-mono text-2xs tabular-nums text-ink-3">
                    관련도 {Math.round(relevance * 100)}%
                  </span>
                )}
              </div>
              {section && (
                <p className="text-2xs text-ink-3">{section}</p>
              )}
              {snippet && (
                <p className="mt-1 text-ui leading-relaxed text-ink-2">
                  {snippet}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
