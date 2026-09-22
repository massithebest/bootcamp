/**
 * Frontend 전용(UI) 타입.  Backend Contract 와 무관하며,
 * 현재 단계에서는 하드코딩된 더미 데이터로 채운다.
 * 향후 Backend Memory / History / Skills API 와 연결할 때의 인터페이스 형태를 잡아 둔다.
 */

/**
 * 에이전트가 선택해 쓰는 Skill. `GET /api/knowledge/skills` 응답 형태다.
 *
 * 활성/비활성 토글은 두지 않는다 — Skills는 읽기 전용이며 텍스트 지식 활성화와는 별개다.
 */
export interface Skill {
  name: string;
  description: string;
  status: string;
}

export interface CurrentUser {
  name: string;
  team: string;
}
