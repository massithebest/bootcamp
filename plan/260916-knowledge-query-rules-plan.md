# 지식 Query 규칙·시각화 안내 계약 개선 계획

**상태: 완료. 작성일: 2026-09-16. 완료일: 2026-09-16.**

## 목표

- table과 recipe 지식에 SQL 작성 시 적용할 기본 필터·날짜·조인 규칙을
  `query_rules: list[str]`로 기록한다.
- table에도 `visualization_hints: list[str]`를 제공한다.
- table과 recipe의 `sample_queries`는 `question`, `sql`만 유지하고 현재 데이터에
  종속되는 `answer`는 제거한다.

## 공유 계약

- `query_rules`는 SQL 작성 전에 적용하는 필터·기준일·정렬·조인 전제다.
- `aggregation_rules`는 집계 grain과 집계 함수, 중복·재집계 규칙이다.
- `visualization_hints`는 표현 권고이며 차트 생성 서비스의 강제 규칙은 아니다.
- 날짜 컬럼이 있는 운영 테이블은 다음과 같은 규칙을 자유 서술형으로 기록할 수 있다.
  - 날짜 미지정 시 `work_dt = CURRENT_DATE`를 적용한다.
  - `plan_dt`는 인터페이스 기준일이므로 별도 요청이 없으면 `CURRENT_DATE`로 제한한다.
- Agent는 사용하는 table과 recipe의 `query_rules`를 SQL에 반영해야 한다.

## 작업 분리

- Backend: 모델·YAML·Tool 설명·SQL Skill·관리 문서·회귀 테스트 갱신.
- Frontend: 구조화 상세의 `query_rules` 라벨과 2필드 샘플 SQL 렌더링 갱신.

## 완료 조건

- 모든 table YAML에 `query_rules`, `visualization_hints`가 있다.
- 모든 recipe YAML에 `query_rules`가 있고 기존 `visualization_hints`가 유지된다.
- table/recipe `sample_queries` 어디에도 `answer`가 없다.
- 로더가 새 계약을 검증하고 Agent 지침이 `query_rules` 적용을 요구한다.
- 백엔드·프론트엔드 테스트와 빌드·린트가 통과한다.

## 검증 결과

- Backend: `262 passed, 6 deselected`
- Frontend: `67 passed`, production build 성공
- ESLint: 오류 0개, 기존 Fast Refresh 경고 13개
- `git diff --check` 통과
