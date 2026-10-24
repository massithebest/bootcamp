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
  "당월 계획 중 실적이 하나도 발생하지 않은 계획을 보여주세요.",
  "등급이 여러 개로 나누어진 제품 알려주세요.",
  "FGS IN 필요량 관리부터 PKT 생산 계획까지, 전체 FP 계획 수립 프로세스는 어떻게 흘러가나요?",
  "2026년 5월 공정별 계획수량 합계 알려주세요.",
  "SEG_A 시뮬레이션 입력 정합성을 검증해 주세요.",
];
