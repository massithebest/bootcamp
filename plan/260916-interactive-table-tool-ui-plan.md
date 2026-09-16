# assistant-ui Tool UI 기반 대화형 표

**상태: 완료. 마지막 갱신: 2026-09-16.**

## 목표와 범위

저장된 SQL·시뮬레이션 결과를 답변 아래의 독립적인 표로 표시하고, 사용자가
브라우저에서 검색·열 정렬·페이지 크기 변경·페이지 이동을 할 수 있게 한다.
기존 표와 Markdown 표의 화면 표시 상한은 10행에서 100행으로 올린다.

## 공유 계약과 결정

- Backend에 `prepare_table(result_id, columns?, title?)` Tool을 추가한다.
- 성공 payload는 `status`, `result_id`, `title`, `columns`, `rows`, `row_count`,
  `displayed_count`, `source_truncated`를 포함한다.
- `rows`는 Result Store에서 읽은 앞쪽 최대 100행이며, 요청한 `columns`가 있으면
  그 순서대로 투영한다. 모델이 원본 행 배열을 입력으로 전달하지 않는다.
- 다른 브라우저 scope, 만료·손상·존재하지 않는 결과는 내부 경로를 노출하지 않는
  안전한 오류로 반환한다.
- Frontend는 `prepare_table`을 render-only backend Tool UI와
  `display: "standalone"`으로 등록한다. 정렬·필터·페이지 이동은 성공 payload의
  최대 100행 안에서 수행한다.
- 모델이 표 요청 뒤 `prepare_table` 호출을 빠뜨리거나 Markdown 표만 작성하면,
  Backend가 마지막 Result Store 결과로 호출을 보완한다. 성공한 Tool UI가 있으면
  Frontend는 같은 응답의 Markdown 표를 제거하고 설명 문장만 유지한다.
- 페이지 크기는 10·25·50·100이며, 검색이나 정렬 변경 시 첫 페이지로 돌아간다.
- 기존 FastAPI SSE, `useExternalStoreRuntime`, Result Store 저장 상한 1,000행과
  폐쇄망 의존성 정책은 유지한다. 새 npm·Python 의존성은 추가하지 않는다.

## 파트별 할당

1. [Backend 실행 계획](../backend/plan/260916-interactive-table-tool-ui-plan.md):
   Result Store 기반 표 서비스·Tool·SDK 등록·Agent 지침·Fake Runner·테스트.
2. [Frontend 실행 계획](../frontend/plan/260916-interactive-table-tool-ui-plan.md):
   standalone Tool UI, 대화형 표, 메시지 순서, 100행 공통 표시 한도와 테스트.

## 완료 조건

- `prepare_table`은 접근 가능한 Result Store 결과만 최대 100행으로 반환한다.
- 성공한 Tool 호출은 최종 설명 아래에서 독립적인 대화형 표로 표시된다.
- 사용자는 전체 100행 범위에서 검색·오름차순/내림차순 정렬과 페이지 이동을
  키보드로 사용할 수 있다.
- 일반 Tool 결과 표와 Markdown 표도 최대 100행까지 표시할 수 있다.
- Backend pytest와 Frontend test/build/lint가 통과하고 계획·Todo·결정 문서가
  현재 구현과 일치한다.

## 완료 결과

- `prepare_table`이 scope·TTL·컬럼을 검증한 Result Store 결과를 최대 100행으로
  반환하며 Agent SDK, Fake Runner와 SQL·시뮬레이션 절차에 연결됐다.
- render-only standalone Tool UI가 최종 설명 아래에서 검색·열 정렬·페이지 크기
  10/25/50/100과 이전·다음 이동을 제공한다.
- 공용 Tool 결과 표와 Markdown 표의 표시 상한도 100행으로 통일했다.
- Backend 234개 테스트 통과(5개 선택 해제), Frontend 44개 테스트·build 통과,
  lint 오류 0(기존 Fast Refresh 경고 13개)과 `git diff --check`를 통과했다.
- 실제 브라우저에서 Fake Runner 표·차트 동시 표시, 검색과 수치 정렬을 확인했다.
  별도 25행 응답으로 10행 단위 다음 페이지와 25행 페이지 크기 전환을 확인했으며
  Vite overlay와 console error는 없었다.
- 후속 실사용 점검에서 장시간 실행 중이던 Backend가 새 Tool 등록 전 코드였고,
  모델도 Markdown 표만 반환할 수 있음을 확인했다. 표 요청·Markdown 표를 감지하는
  Backend 자동 보완과 성공 Tool UI의 중복 Markdown 제거를 추가했다. 기존 메시지는
  Tool 호출 이력이 없으므로 재생성하거나 다시 질문할 때 대화형 표로 전환된다.
- 실행 중 Backend를 재시작한 뒤 실제 Agent에 `part_1` Route 30행 표를 요청해
  검색 필터, `step` 내림차순 정렬, 다음 페이지(11~20행), 페이지 크기 25 전환을
  확인했다. Vite overlay와 브라우저 console error는 없었다.
