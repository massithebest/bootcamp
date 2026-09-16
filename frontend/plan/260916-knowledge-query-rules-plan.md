# 지식 Query 규칙·시각화 안내 Frontend 실행 계획

**상태: 완료. 상위 계획:**
[지식 Query 규칙·시각화 안내 계약 개선](../../plan/260916-knowledge-query-rules-plan.md)

## Task

1. 구조화 지식 상세에 `query_rules`를 `조회 규칙`으로 표시한다.
2. `sample_queries`를 질문과 SQL만 있는 계약으로 렌더링한다.
3. 기존 2열 구조, 긴 텍스트 줄바꿈과 SQL 스크롤 규칙을 유지한다.

## 검증

- `npm test`
- `npm run build`
- `npm run lint`

## 실행 결과

- 테스트: `67 passed`
- production build 성공
- ESLint 오류 0개, 기존 Fast Refresh 경고 13개
- `query_rules`는 기존 읽기 쉬운 불릿 목록으로 표시하고 샘플 SQL에서 답변
  블록을 제거했다.
