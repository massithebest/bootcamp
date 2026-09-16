# TanStack Table 전환과 표·차트 문맥 배치

**상태: 완료. 마지막 갱신: 2026-09-16.**

## 목표와 범위

대화형 표의 직접 구현 정렬·필터·페이지 상태를 TanStack Table로 교체하고,
표·차트 Tool UI와 각 설명을 실제 메시지 발생 순서대로 함께 표시한다.
기존 Result Store, `prepare_table`, `prepare_visualization`, Recharts와 최대 100행
payload 계약은 유지한다.

## 공유 결정

- `@tanstack/react-table`은 정확한 버전을 lockfile에 고정한다. Recharts는 현재
  3.8.0을 유지한다.
- 두 프로젝트은 MIT 라이선스이며 배포물의 제3자 고지에 저작권·라이선스 전문을
  보존한다.
- 현재 개발 registry는 공개 npm이므로 사내 Nexus 보유 여부는 폐쇄망 환경에서
  정확한 버전과 전이 의존성을 대상으로 별도 확인한다.
- 일반 실행 Tool은 기존 실행 과정 그룹에 둔다. `prepare_table`과
  `prepare_visualization`은 standalone을 유지하되 답변 끝으로 재배치하지 않고
  `MessagePart[]`의 text/tool 순서를 보존한다.
- Agent는 각 표현마다 `도입 설명 → prepare_* 호출 → 결과 해석` 순서로 응답한다.
  자동 보완 표는 답변 완료 뒤 생기는 복구 이벤트이므로 마지막에 표시될 수 있다.

## 파트별 할당

1. [Backend 실행 계획](../backend/plan/260916-tanstack-table-message-order-plan.md):
   Agent·Skill 지침과 Fake Runner의 설명/Tool 순서 및 회귀 테스트.
2. [Frontend 실행 계획](../frontend/plan/260916-tanstack-table-message-order-plan.md):
   TanStack Table 전환, 원래 메시지 순서 보존, 라이선스·폐쇄망 기록과 검증.

## 완료 조건

- 기존 검색·단일 열 3상태 정렬·10/25/50/100 페이지 기능과 접근성을 유지한다.
- `text → table → text → chart → text` 이벤트가 같은 순서로 화면에 표시된다.
- package/lockfile이 일치하고 test/build/lint 및 실제 브라우저 검증을 통과한다.
- Nexus 확인 명령과 MIT 고지 의무가 내부 URL·인증값 없이 문서에 기록된다.

## 완료 기록

- `@tanstack/react-table` 9.2.4와 Recharts 3.8.0을 정확한 버전으로 고정하고,
  필터·3상태 정렬·10/25/50/100 페이지 상태를 TanStack row model로 전환했다.
- standalone 표·차트와 공개 설명을 `MessagePart[]` 순서대로 렌더링하고 Agent 지침과
  Fake Runner도 `도입 설명 → Tool UI → 결과 해석` 순서로 맞췄다.
- MIT 전문을 배포 asset에 포함하고 Nexus 직접 조회와 빈 cache `npm ci` 절차를
  폐쇄망 문서에 기록했다. 현재 환경은 공개 npm이어서 사내 Nexus 보유 여부 자체는
  폐쇄망 준비 환경에서 확인해야 한다.
- frontend test 45건, build, lint(기존 Fast Refresh 경고 13건), backend test 234건과
  실제 브라우저의 검색·정렬·100행 선택·Recharts SVG·문맥 순서를 검증했다.


## 통합 검토 보완 (2026-09-16)

표·차트 뒤 추가 일반 Tool 조회가 있어도 앞선 도입·표현·해석 구간을 유지한다.
마지막 일반 Tool 이후만 렌더링하던 누락을 수정했다. 검증과 잔여 위험은
[통합 검토](260916-uncommitted-review-plan.md)에 기록했다.
