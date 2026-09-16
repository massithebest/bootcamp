# 개발 지침·README 동기화 계획

**상태: 완료. 작성일: 2026-09-16. 완료일: 2026-09-16.**

## 목표

현재 구현을 기준으로 루트·Backend·Frontend의 `AGENTS.md`, `CLAUDE.md`,
`README.md`를 동기화한다.

## 범위

- 현재 기능, 실행·검증 명령, mock/real 경계와 API 진입점 정리
- `query_rules`, `aggregation_rules`, `visualization_hints`, 2필드
  `sample_queries` 지식 계약 반영
- `.playwright-mcp`, 로컬 dataset·변환 스크립트 등 Git 제외 산출물 안내
- Frontend의 응답 시간, 지식 상세, 브라우저 검증 페이지 설명 갱신
- `CLAUDE.md`의 호환 진입점과 런타임 Agent 지침 역할 구분 유지

## 비범위

- 애플리케이션 코드와 API 계약 변경
- 완료된 개별 기능 계획의 실행 이력 재작성
- 외부 반입 소스의 라이선스·원본 hash 변경

## 완료 조건

- 각 문서의 설명과 현재 코드·설정이 일치한다.
- 상대 링크가 존재하고 `git diff --check`가 통과한다.
- 문서만 변경하므로 애플리케이션 전체 테스트는 생략할 수 있다.

## 검증 결과

- 현재 코드·환경 예시·패키지 버전과 실행 명령 대조 완료
- 대상 Markdown 25개 상대 링크 검사: 누락 0개
- `git diff --check` 통과
- 애플리케이션 코드는 변경하지 않아 전체 테스트는 생략했다.
