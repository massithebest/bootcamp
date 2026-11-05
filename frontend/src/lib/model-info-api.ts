import { API_BASE_URL } from "./chat-api";

const FALLBACK_NAME = "기본 모델";
let cachedName: string | undefined;

async function request(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/model-info`);
  if (!response.ok) throw new Error(`model-info ${response.status}`);
  const body: unknown = await response.json();
  const name = typeof body === "object" && body !== null ? (body as { display_name?: unknown }).display_name : undefined;
  if (name !== null && typeof name !== "string") throw new Error("model-info payload");
  return name || FALLBACK_NAME;
}

let pending: Promise<string> | null = null;

/** 입력창이 다시 나타날 때 깜빡이거나 다시 조회하지 않도록 서버 값을 기억한다(설정은 기동 중 바뀌지 않는다). */
export const cachedModelDisplayName = () => cachedName;

/** 표시 이름을 돌려준다. 조회에 실패하면 이번에는 기본 문구를 쓰고, 다음 새로고침에서 다시 읽는다. */
export function fetchModelDisplayName(): Promise<string> {
  pending ??= request()
    .catch(() => FALLBACK_NAME)
    .then((name) => (cachedName = name));
  return pending;
}
