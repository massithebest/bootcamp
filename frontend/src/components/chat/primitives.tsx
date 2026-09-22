/**
 * 공용 UI 조각. 외부 컴포넌트 라이브러리 / 아이콘 패키지를 쓰지 않고 직접 작성한다.
 * 구분은 카드가 아니라 1px 룰과 배경 톤으로 만든다.
 */

import {
  useId,
  useState,
  type ReactNode,
} from "react";
export const TABLE_DISPLAY_ROW_LIMIT = 100;

export type Tone = "neutral" | "ok" | "warn" | "block" | "accent";

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-ink-2",
  ok: "text-ok-ink",
  warn: "text-warn-ink",
  block: "text-block-ink",
  accent: "text-accent",
};

const TONE_DOT: Record<Tone, string> = {
  neutral: "bg-ink-3",
  ok: "bg-ok-ink",
  warn: "bg-warn-ink",
  block: "bg-block-ink",
  accent: "bg-accent",
};

/** 상태를 색으로 말하되 최소한으로 — 채운 점 하나. */
export function StatusDot({
  tone,
  pulse = false,
  className = "",
}: {
  tone: Tone;
  pulse?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${TONE_DOT[tone]} ${
        pulse ? "motion-safe:animate-pulse" : ""
      } ${className}`}
      aria-hidden
    />
  );
}

/** 작은 상태/도구 표식. 대문자·배지 남용을 피하고 옅은 틴트만 쓴다. */
export function Tag({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  const bg: Record<Tone, string> = {
    neutral: "bg-surface-2 text-ink-2",
    ok: "bg-ok-weak text-ok-ink",
    warn: "bg-warn-weak text-warn-ink",
    block: "bg-block-weak text-block-ink",
    accent: "bg-accent-weak text-accent",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-2xs font-medium ${bg[tone]}`}
    >
      {children}
    </span>
  );
}

export function ToneText({
  tone,
  children,
}: {
  tone: Tone;
  children: ReactNode;
}) {
  return <span className={TONE_TEXT[tone]}>{children}</span>;
}

/**
 * 접이식 영역. 등장 효과 없이 높이만 전환한다.
 * `chevron` 은 회전하는 작은 삼각형 (아이콘 패키지 미사용).
 */
export function Disclosure({
  summary,
  defaultOpen = false,
  children,
  dense = false,
}: {
  summary: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
  dense?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-1.5 text-left text-ui text-ink-2 transition-colors hover:text-ink ${
          dense ? "py-1" : "py-1.5"
        }`}
      >
        <Chevron open={open} />
        <span className="min-w-0 flex-1">{summary}</span>
      </button>
      {open && (
        <div id={panelId} className="pb-1 pl-[1.125rem]">
          {children}
        </div>
      )}
    </div>
  );
}

export function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 10 10"
      width="9"
      height="9"
      className={`shrink-0 text-ink-3 transition-transform duration-150 ease-panel ${
        open ? "rotate-90" : ""
      }`}
      aria-hidden
    >
      <path d="M3 1.5 7 5 3 8.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 수평 구분선 대신 쓰는 얇은 룰 + 라벨 (대문자 아님). */
export function RuleLabel({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-2 py-1">
      <span className="text-2xs font-medium text-ink-3">{children}</span>
      <span className="h-px flex-1 bg-line" />
    </div>
  );
}

/**
 * 데이터 표 — mono, tabular-nums, 얇은 행 구분.
 * payload에는 분석·요약용 원본 행이 더 들어 있어도 화면에는 최대 100개
 * 데이터 행만 표시한다. 가로 스크롤은 기존과 동일하게 유지한다.
 */
export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: string[][];
}) {
  const visibleRows = rows.slice(0, TABLE_DISPLAY_ROW_LIMIT);
  const omittedRows = rows.length - visibleRows.length;

  return (
    <div>
      <div className="thin-scroll max-h-96 overflow-x-auto overflow-y-auto">
        <table className="w-full border-collapse font-mono text-data tabular-nums">
          <thead>
            <tr className="border-b border-line-strong text-left text-ink-2">
              {columns.map((c) => (
                <th key={c} className="whitespace-nowrap px-2 py-1.5 font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, i) => (
              <tr key={i} className="border-b border-line last:border-0">
                {row.map((cell, j) => (
                  <td
                    key={j}
                    className={`whitespace-nowrap px-2 py-1.5 ${
                      j === 0 ? "text-ink-2" : "text-ink"
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {omittedRows > 0 && (
        <p className="border-t border-line px-2 py-1.5 text-2xs text-ink-2">
          전체 {rows.length.toLocaleString("ko-KR")}건 중 {TABLE_DISPLAY_ROW_LIMIT}건 표시 · {omittedRows.toLocaleString("ko-KR")}건 생략
        </p>
      )}
    </div>
  );
}
