# 좌측 전역 내비게이션 Frontend 실행 계획

**상태: 완료 (2026-09-16). 상위: [공통 계획](../../plan/260916-sidebar-navigation-plan.md).**

## 작업

1. `app-sidebar.tsx`: 상단 전역 메뉴와 최근 대화 영역을 분리하고 현재 목적지를
   `aria-current`와 배경 상태로 표시한다.
2. `chat-window.tsx`: 좌측 `채팅` 메뉴에 상태 보존 복귀를 연결하고 중앙 헤더의
   별도 복귀 버튼을 제거한다.
3. 지식 관리의 미저장 이동 확인, Composer/스트리밍/스크롤 보존 회귀를 갱신한다.
4. `frontend/CLAUDE.md`와 기술 결정 기록을 최종 동작에 맞춘다.

## 검증

- `npm test`
- `npm run build`
- `npm run lint`
- 브라우저에서 채팅 → 지식 관리 → 채팅, 현재 메뉴 상태, 최근 대화 선택,
  좁은 폭에서 사이드바 재열기를 확인한다.

## 실행 기록

- `ui-ux-pro-max`의 전역 내비게이션·현재 위치·키보드 탐색 지침을 적용했다.
- assistant-ui Thread는 언마운트하지 않고 기존 External Store와 비영속 예시
  ThreadList 경계를 유지한다.
- `npm test` 52개, `npm run build`, `npm run lint`를 통과했다. lint에는 기존
  Fast Refresh 경고 13개만 남고 오류는 없다.
- 실제 브라우저에서 채팅/지식 관리의 `aria-current`, Composer 초안 보존,
  중앙 복귀 버튼 제거와 400px 수평 overflow 없음·사이드바 재열기를 확인했다.
- 지식 워크스페이스 브라우저 회귀 4개가 모두 통과했다.
