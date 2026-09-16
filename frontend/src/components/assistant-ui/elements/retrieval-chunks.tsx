/** Adapted from assistant-ui elements/retrieval-chunks. No synthetic threshold or score. */
import { DatabaseIcon } from "lucide-react";

export interface RetrievalChunk {
  id: string;
  source: string;
  locator?: string | null;
  score?: number | null;
  text?: string | null;
}

export function RetrievalChunks({ query, chunks }: { query?: string | null; chunks: readonly RetrievalChunk[] }) {
  return (
    <div data-slot="retrieval-chunks" className="flex min-w-0 flex-col gap-2.5">
      {query && <p className="flex items-start gap-2 text-2xs text-ink-2"><DatabaseIcon aria-hidden className="size-3.5 shrink-0" /><span className="break-words">검색어 {query}</span></p>}
      <p className="text-2xs text-ink-3">{chunks.length ? `검색 문서 ${chunks.length}개` : "검색된 문서가 없습니다."}</p>
      <ul className="flex flex-col gap-2">
        {chunks.map((chunk) => {
          const score = typeof chunk.score === "number" && Number.isFinite(chunk.score) && chunk.score >= 0 && chunk.score <= 1 ? chunk.score : null;
          const percent = score === null ? null : Math.round(score * 100);
          return (
            <li key={chunk.id} className="flex min-w-0 flex-col gap-1.5 rounded border border-line bg-canvas p-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <span className="min-w-0 break-words text-ui font-medium text-ink">{chunk.source}</span>
                {percent !== null && <span className="shrink-0 font-mono text-2xs tabular-nums text-ink-3">관련도 {percent}%</span>}
              </div>
              {chunk.locator && <p className="break-words text-2xs text-ink-3">{chunk.locator}</p>}
              {chunk.text && <p className="whitespace-pre-wrap break-words text-ui leading-relaxed text-ink-2">{chunk.text}</p>}
              {percent !== null && (
                <span role="meter" aria-label={`${chunk.source} 검색 관련도`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-0.5 overflow-hidden rounded bg-surface-2">
                  <span className="block h-full bg-accent" style={{ width: `${percent}%` }} />
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
