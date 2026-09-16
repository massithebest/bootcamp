import { useEffect, useState } from "react";

/** Read requests are cancelled when selection changes; explicit retry and shared invalidation. */
export function useKnowledgeResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({ loading: true });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const refresh = () => setRevision(v => v + 1);
    window.addEventListener("knowledge-changed", refresh);
    return () => window.removeEventListener("knowledge-changed", refresh);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true });
    load(controller.signal).then(data => { if (!controller.signal.aborted) setState({ data, loading: false }); })
      .catch((error: unknown) => { if (!controller.signal.aborted) setState({ error: error instanceof Error ? error.message : "불러오지 못했습니다.", loading: false }); });
    return () => controller.abort();
  }, [load, revision]);
  return { ...state, reload: () => setRevision(v => v + 1) };
}
