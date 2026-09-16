import { RefreshCwIcon } from "lucide-react";
import { ErrorState } from "@/components/assistant-ui/elements/error-state";
import { ghostButton } from "@/components/assistant-ui/elements/surfaces";

export function ConnectionBanner({ onRetry, retrying }: { onRetry: () => void; retrying: boolean }) {
  return <ErrorState
    title="서버에 연결하지 못했습니다"
    detail="마지막 요청이 응답을 받지 못했습니다. 대화 내용은 유지되며 같은 질문을 다시 시도할 수 있습니다."
    action={<button type="button" onClick={onRetry} disabled={retrying} className={`${ghostButton} inline-flex items-center gap-1.5 px-2 py-1.5 text-2xs`}><RefreshCwIcon aria-hidden className="size-3.5" />{retrying ? "다시 시도 중…" : "마지막 질문 다시 시도"}</button>}
  />;
}
