# 지식 Query 규칙·시각화 안내 Backend 실행 계획

**상태: 완료. 상위 계획:**
[지식 Query 규칙·시각화 안내 계약 개선](../../plan/260916-knowledge-query-rules-plan.md)

## Task

1. `KnowledgeTable`과 `KnowledgeRecipe`에 `query_rules`를 추가하고 table에
   `visualization_hints`를 추가한다.
2. 샘플 쿼리 계약을 `question`·`sql` 두 필드로 제한한다.
3. 모든 table/recipe YAML과 관리 문서, Agent SQL 절차를 새 계약으로 갱신한다.
4. 로더·Tool·실제 지식 정합성 회귀 테스트를 보강한다.

## 검증

- `python -m pytest -q`
- `git diff --check`

## 실행 결과

- 전체 테스트: `262 passed, 6 deselected`
- 샘플 쿼리의 제거된 `answer` 필드는 로더가 거부하도록 회귀 테스트를 추가했다.
- 모든 실제 table/recipe의 `query_rules`와 table의 `visualization_hints` 존재를
  정합성 테스트로 고정했다.
