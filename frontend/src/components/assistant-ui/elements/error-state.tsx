/** Adapted from assistant-ui elements/error-state; runtime actions supplied as a slot. */
import type { ReactNode } from "react";
import { AlertTriangleIcon } from "lucide-react";

export function ErrorState({ title, detail, action }: {
  title: string;
  detail: ReactNode;
  action: ReactNode;
}) {
  return (
    <div data-slot="error-state" role="alert" className="flex min-w-0 items-start gap-3 rounded border border-line-strong bg-block-weak p-3 text-ui">
      <AlertTriangleIcon aria-hidden className="mt-0.5 size-4 shrink-0 text-block-ink" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="font-medium text-ink">{title}</p>
        <div className="break-words text-ink-2">{detail}</div>
        <div className="flex flex-wrap gap-2">{action}</div>
      </div>
    </div>
  );
}
