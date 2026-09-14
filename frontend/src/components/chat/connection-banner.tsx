/**
 * 백엔드 연결 실패 상태.  붉은 문장 한 줄로 두지 않고,
 * 무엇이 실패했고 무엇을 하면 되는지 알려준다.
 */

import { API_BASE_URL } from "@/lib/chat-api";

export function ConnectionBanner({
  onRetry,
  retrying,
}: {
  onRetry: () => void;
  retrying: boolean;
}) {
  return (
    <div className="border-l-2 border-warn-ink bg-warn-weak px-3.5 py-3">
      <p className="text-ui font-medium text-ink">
        백엔드에 연결하지 못했습니다
      </p>
      <p className="mt-1 text-ui leading-relaxed text-ink-2">
        마지막 요청이 응답을 받지 못했습니다. 대화 내용은 그대로 유지됩니다.
      </p>

      <ul className="mt-2 flex flex-col gap-1 text-2xs text-ink-2">
        <li>
          · 요청 주소{" "}
          <span className="font-mono text-ink">{API_BASE_URL}/api/chat</span>
        </li>
        <li>· 백엔드(FastAPI) 서버가 실행 중인지 확인하세요.</li>
        <li>
          · 원격 접속(SSH) 환경이면 해당 포트가 포워딩됐는지 확인하세요.
        </li>
        <li>
          · 브라우저 콘솔에 CORS 오류가 보이면 백엔드의 허용 Origin 설정을
          확인하세요.
        </li>
      </ul>

      <button
        type="button"
        onClick={onRetry}
        disabled={retrying}
        className="mt-2.5 rounded border border-line-strong bg-canvas px-2.5 py-1 text-2xs font-medium text-ink transition-colors hover:bg-surface-2 disabled:opacity-60"
      >
        {retrying ? "다시 시도 중…" : "마지막 질문 다시 시도"}
      </button>
    </div>
  );
}
