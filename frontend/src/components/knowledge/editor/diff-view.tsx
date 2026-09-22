import { collapseUnchanged, diffLines, hasChanges } from "@/lib/line-diff";

const ROW_STYLE = { same: "", add: "bg-ok-weak", del: "bg-block-weak" } as const;
const SYMBOL = { same: " ", add: "+", del: "−" } as const;
const SR_LABEL = { same: "", add: "추가", del: "삭제" } as const;

/** 현재 승인본과 제안 내용의 줄 단위 차이. 추가·삭제는 색과 기호·읽기 전용 텍스트로 함께 전달한다. */
export function DiffView({ before, after }: { before: string; after: string }) {
  const rows = diffLines(before, after);
  if (!hasChanges(rows)) return <p className="text-ui text-ink-3">현재 승인본과 달라진 내용이 없습니다.</p>;
  const chunks = collapseUnchanged(rows);
  const added = rows.filter(r => r.kind === "add").length;
  const removed = rows.filter(r => r.kind === "del").length;
  return <div className="space-y-2">
    <p className="text-2xs tabular-nums text-ink-2">{added}줄 추가 · {removed}줄 삭제{before === "" ? " · 새 지식입니다" : ""}</p>
    <div role="group" aria-label="변경 내용" className="thin-scroll max-h-[28rem] overflow-auto border border-line">
      <ol className="font-mono text-data">
        {chunks.map((chunk, index) => chunk.kind === "gap"
          ? <li key={index} className="border-y border-line bg-surface px-3 py-1 text-2xs text-ink-3">변경 없는 {chunk.count}줄</li>
          : <li key={index} className={`flex ${ROW_STYLE[chunk.kind]}`}>
            <span aria-hidden className="w-9 shrink-0 select-none pr-2 text-right tabular-nums text-ink-3">{chunk.newNo ?? chunk.oldNo}</span>
            <span aria-hidden className="w-4 shrink-0 select-none text-center">{SYMBOL[chunk.kind]}</span>
            <span className="min-w-0 flex-1 whitespace-pre-wrap break-words pr-3">{SR_LABEL[chunk.kind] && <span className="sr-only">{SR_LABEL[chunk.kind]}: </span>}{chunk.text || " "}</span>
          </li>)}
      </ol>
    </div>
  </div>;
}
