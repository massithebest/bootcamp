/**
 * 초기 화면용 생산계획 예시 데이터.
 * 합성 mock SQLite 조회와 문서 검색(RAG) 결과만 사용하며 특정 세그먼트를
 * 지정하지 않는다.
 */

import type { CurrentUser } from "@/types/workspace";

export const CURRENT_USER: CurrentUser = {
  name: "손흥민",
  team: "생산관리팀 · 계획파트",
};

export const EXAMPLE_QUESTIONS: string[] = [
  "FAC_ID별 계획수량과 실적수량 합계를 보여줘.",
  "실적이 계획을 초과해 swap이 발생한 제품을 보여줘.",
  "잔여계획수량이 가장 큰 제품 상위 10개를 알려줘.",
  "Hotlot은 무엇을 의미해?",
  "Setup Group은 왜 필요해?",
  "MTTF와 MTTR의 차이가 뭐야?",
];
