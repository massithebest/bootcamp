import { useEffect, useRef, useState } from "react";

/** Restore focus before auto-collapse removes a focused descendant. */
export function useExecutionDisclosure(running: boolean, expandWhileRunning = true) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(running && expandWhileRunning);
  useEffect(() => {
    if (!running) {
      const root = rootRef.current;
      const content = root?.querySelector("[data-disclosure-content]");
      if (content?.contains(document.activeElement)) {
        root?.querySelector<HTMLElement>("[data-disclosure-trigger]")?.focus({ preventScroll: true });
      }
      setOpen(false);
    } else if (expandWhileRunning) setOpen(true);
  }, [running, expandWhileRunning]);
  return { rootRef, open, setOpen };
}
