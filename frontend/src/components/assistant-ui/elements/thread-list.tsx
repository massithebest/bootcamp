/** Adapted from assistant-ui elements-thread-list. Props driven: no persistence implied. */
import type { ComponentProps } from "react";
import { MessageSquareIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ThreadItem {
  id: string;
  title: string;
  time: string;
}

export function ThreadList({ threads, activeIndex, onActiveIndexChange, label, className, ...props }: ComponentProps<"div"> & {
  threads: readonly ThreadItem[];
  activeIndex: number;
  onActiveIndexChange: (index: number) => void;
  label: string;
}) {
  return (
    <div data-slot="thread-list" className={cn("flex w-full flex-col gap-0.5", className)} {...props}>
      <p className="px-2 py-2 text-2xs text-ink-3">{label}</p>
      {threads.map((thread, i) => (
        <button key={thread.id} type="button" aria-current={i === activeIndex || undefined}
          onClick={() => onActiveIndexChange(i)}
          className={cn("flex w-full items-start gap-2 rounded px-2 py-2 text-left transition-colors", i === activeIndex ? "bg-accent-weak text-ink" : "text-ink-2 hover:bg-surface-2")}>
          <MessageSquareIcon className="mt-1 size-3.5 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-ui">{thread.title}</span>
            <span className="block text-2xs text-ink-3">{thread.time}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
