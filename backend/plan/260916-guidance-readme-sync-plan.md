# Backend 개발 지침·README 동기화 실행 계획

**상태: 완료. 상위 계획:**
[개발 지침·README 동기화](../../plan/260916-guidance-readme-sync-plan.md)

## Task

1. Backend 계층, API, Result Store와 지식 관리 경계를 README에 반영한다.
2. `AGENTS.md`에 최신 table/recipe 지식 필드 계약과 검증 규칙을 추가한다.
3. 개발용 `CLAUDE.md`와 런타임 Agent용 `CLAUDE.md`의 역할을 명확히 유지한다.

## 검증

- 문서 링크·명령·환경변수를 현재 파일과 대조한다.
- `git diff --check`

## 실행 결과

- Backend 지침·호환 진입점·런타임 Agent 지침·README를 현재 지식·결과 계약과
  mock/real 경계에 맞춰 갱신했다.
- 링크·명령·환경변수 대조와 `git diff --check`를 통과했다.
