/**
 * 인증 체계가 생기기 전 임시 사용자 선택. 실제 인증이 아니며 요청 헤더로 작성자·승인자를 구분해 기록하는 용도다.
 * localStorage 는 없거나 막혀 있어도 동작해야 하므로 모든 접근을 보호한다.
 */
const STORAGE_KEY = "pp.knowledge.stub-user";

export function getStubUserId(): string {
  try { return window.localStorage.getItem(STORAGE_KEY) ?? ""; } catch { return ""; }
}

export function setStubUserId(userId: string): void {
  try { window.localStorage.setItem(STORAGE_KEY, userId); } catch { /* 저장 실패 시 이번 세션만 기본 사용자를 쓴다 */ }
  // 목록·권한이 모두 사용자에 따라 달라지므로 공용 무효화 이벤트를 쓴다.
  window.dispatchEvent(new Event("knowledge-changed"));
}
