import { useEffect, useRef, useState } from "react";
import { CheckIcon, CopyIcon, TriangleAlertIcon } from "lucide-react";

import { Disclosure } from "../primitives";

type CopyState = "idle" | "copied" | "failed";

/** 실행 SQL을 기본 접힘으로 보여 준다. SQL은 text node로만 렌더링한다. */
export function SqlPreview({ sql, title }: { sql: string; title?: string }) {
  const [copy, setCopy] = useState<CopyState>("idle");
  const timer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(timer.current), []);

  const copySql = () => {
    const finish = (next: CopyState) => {
      setCopy(next);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopy("idle"), 3000);
    };
    if (typeof navigator === "undefined" || !navigator.clipboard) {
      finish("failed");
      return;
    }
    navigator.clipboard.writeText(sql).then(() => finish("copied"), () => finish("failed"));
  };

  const Icon = copy === "copied" ? CheckIcon : copy === "failed" ? TriangleAlertIcon : CopyIcon;

  return (
    <section data-slot="sql-preview" className="min-w-0">
      <Disclosure summary={title ?? "실행 SQL"} dense>
        <div className="mt-1 flex flex-col gap-1.5">
          <div className="flex items-center justify-end gap-2">
            <span role="status" className="text-2xs text-ink-2">
              {copy === "copied" ? "복사됨" : copy === "failed" ? "복사하지 못했습니다" : ""}
            </span>
            <button
              type="button"
              onClick={copySql}
              aria-label="SQL 복사"
              className="inline-flex items-center gap-1 rounded border border-line-strong px-2 py-1 text-2xs text-ink-2 hover:bg-surface-2"
            >
              <Icon aria-hidden className="size-3" />
              복사
            </button>
          </div>
          <pre
            tabIndex={0}
            aria-label="실행 SQL 전체 내용"
            className="thin-scroll max-h-96 overflow-auto rounded bg-[#1c2530] px-3 py-2.5 font-mono text-data leading-relaxed tabular-nums text-[#d7dce4]"
          >
            {sql}
          </pre>
        </div>
      </Disclosure>
    </section>
  );
}
