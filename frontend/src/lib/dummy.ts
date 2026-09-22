/**
 * 초기 화면용 생산계획 benchmark 예시 데이터.
 * 수치는 원본을 변환한 SQLite 조회 및 입력 정합성 mock 결과만 사용한다.
 */

import type { CurrentUser } from "@/types/workspace";

export const CURRENT_USER: CurrentUser = {
  name: "손흥민",
  team: "생산관리팀 · 계획파트",
};

export const EXAMPLE_QUESTIONS: string[] = [
  "LVHM에서 제품별 초기 WIP Lot과 piece 수를 조회해줘.",
  "LVHM part_1의 공정 Route를 순서대로 보여줘.",
  "HVLM의 Dry Etch 설비는 Family별로 몇 대 있어?",
  "LVHM 제품별 전체 공정 Step 수를 알려줘.",
  "HVLM에서 납기가 가장 빠른 WIP와 신규 투입 Lot을 보여줘.",
  "생산계획 LVHM 입력 테이블의 관계를 검증해줘.",
];
