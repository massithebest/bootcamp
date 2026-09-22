import type { ReactNode } from "react";

/** loading·empty·error 상태를 같은 표면으로 보여 주는 안내 블록. */
export function ResultNotice({
  children,
  tone = "neutral",
  loading = false,
  className = "",
}: {
  children: ReactNode;
  tone?: "neutral" | "alert";
  loading?: boolean;
  className?: string;
}) {
  return (
    <div
      role={tone === "alert" ? "alert" : "status"}
      aria-busy={loading || undefined}
      className={`flex min-h-24 flex-col items-center justify-center gap-2 rounded border border-line bg-surface-2 px-4 py-3 text-center text-ui text-ink-2 ${className}`}
    >
      {children}
    </div>
  );
}

export function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border border-line-strong px-2 py-1 text-2xs text-ink-2 hover:bg-surface"
    >
      다시 시도
    </button>
  );
}
