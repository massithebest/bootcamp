/** Adapted from assistant-ui elements-tool-call; adds rich result and error slots. */
import type { ReactNode } from "react";
import { AlertCircleIcon, CheckIcon, ChevronRightIcon, LoaderIcon } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { collapsePanel } from "./surfaces";

export function ToolCall({ label, running = false, incomplete = false, open, onOpenChange, error, children, className }: {
  label: string;
  running?: boolean;
  incomplete?: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  error?: string | null;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Collapsible data-slot="tool-call" open={open} onOpenChange={onOpenChange} className={cn("min-w-0 border-l border-line-strong pl-3", className)}>
      <CollapsibleTrigger className="group/trigger flex w-full items-center gap-2 rounded py-1.5 text-left text-2xs text-ink-2 hover:text-ink">
        <ChevronRightIcon aria-hidden className="size-3.5 shrink-0 transition-transform group-data-panel-open/trigger:rotate-90 motion-reduce:transition-none" />
        <span className="min-w-0 flex-1 break-words">{label}</span>
        <span className={cn("flex shrink-0 items-center gap-1", error ? "text-block-ink" : incomplete ? "text-warn-ink" : running ? "text-accent" : "text-ok-ink")}>
          {error || incomplete ? <AlertCircleIcon className="size-3" /> : running ? <LoaderIcon className="size-3 motion-safe:animate-spin" /> : <CheckIcon className="size-3" />}
          {error ? "오류" : incomplete ? "미완료" : running ? "진행" : "완료"}
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent className={collapsePanel}>
        <div className="min-w-0 py-2">
          {error && <p role="alert" className="mb-3 whitespace-pre-wrap break-words text-ui text-block-ink">{error}</p>}
          {children}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
