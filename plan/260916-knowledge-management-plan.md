# 도메인 지식 관리와 조회 패널

**상태: 이번 범위 구현·검증 완료 (2026-09-16). 마지막 갱신: 2026-09-16.**

## 목표와 범위

텍스트 등록 → 검토 → 활성화 → Agent 검색 → 정확한 버전 출처 확인을 제공한다.
좌측 지식 관리 메뉴, 중앙 목록·편집·검토 화면, 우측 도구·스킬·지식 조회 탭을 둔다.
메타·프롬프트 예시 탭은 제거한다. 구조화 YAML은 읽기 전용이며 텍스트는 별도 SQLite에 저장한다.
인증 없는 신뢰된 내부 운영자 공용 모드로 동작하며 별도 활성화 설정을 요구하지 않는다.
Milvus·임베딩·파일 업로드·실제 생산 부진 원인 진단은 후속 범위다.

## 공유 계약

- 기존 skills/catalog/kpis 응답을 유지하고, 구조화 YAML은 `/entries`에서 항상 조회한다.
- `/api/knowledge/tools`: SDK 등록 정의의 name/description/input_schema, output 설명, status=available.
- `/api/knowledge/skills/{name}`: name/description/status/content(절차 본문).
- `/api/knowledge/entries`: type/id/title/summary/status/source/owner/updated, 구조화 항목의 active=null.
  type은 document/table/kpi/recipe/glossary/simulation. 상세는 `/entries/{type}/{id}`.
- `/api/knowledge/documents`: GET 목록, POST 등록. `/documents/{id}` GET 상세, PUT 새 초안.
- 상세는 id/revision/active_version/archived/versions/history. 버전은 version/title/content/category/tags/owner/source/status/created_at/reviewer/review_note/reviewed_at.
- PUT 및 POST `/documents/{id}/{review|activate|deactivate|archive}`는 expected_revision 필수.
  review/activate는 version, review는 actor/note 필수. 충돌은 409로 반환한다.
- 새 버전은 draft. review는 verified 전환, activate는 검토본 검색 포인터 변경.
  수정 중 이전 검색 버전 유지. archive는 복구 없는 보관이며 버전 조회는 유지.
- `/documents/{id}/versions/{version}`은 인용한 불변 본문 조회.
- search_knowledge(query)는 local 기본, kind=knowledge/status/query/documents 유지.
  결과에 document_id/version/title/source/snippet/content/verified 포함. 활성 검토본만 반환.
- 관리 변경은 모든 대화의 이후 검색에 적용. 기존 대화 내용을 소급 삭제하지 않는다.
- SQL 서비스 모드와 문서 검색 backend는 독립 설정. 외부 연결은 이번에 추가하지 않는다.

## 파트별 작업과 완료 조건

[Backend 실행 계획](../backend/plan/260916-knowledge-management-plan.md),
[Frontend 실행 계획](../frontend/plan/260916-knowledge-management-plan.md)을 따른다.
저장·검토·검색 상태 전이, 충돌, 재기동, 출처 링크, 화면 왕복 상태 보존과 기본 검증을 통과해야 한다.
SMT2020 관계 누락·dataset 혼합·중복 집계는 테스트 fixture에서 재현하며 원본은 수정하지 않는다.

## 결정 기록

- 2026-09-16: 사용자 확정 — 좌측 관리/우측 조회, 텍스트 편집만, 기존 검토본 유지,
  내부 공용 관리, local 검색 우선. Phase 3는 완료 처리하지 않는다.
- 2026-09-16: 별도 관리 활성화 환경변수를 제거했다. 기존 구조화 YAML은 항상
  읽기 전용으로 표시하고 텍스트 관리 API는 내부 공용 기능으로 바로 제공한다.
- 2026-09-16: table과 recipe의 SQL 예시는 `question`, `sql`, `answer`로 통일하고
  현재 SMT2020 SQLite 실행 결과를 답변 예시로 기록한다.
- 2026-09-16: 우측 패널 순서를 도구·스킬·지식으로 바꾸고, 지식은 제목·상태와
  짧은 설명을 함께 표시한다. 출처와 관리 화면 이동 링크는 우측에서 제거한다.
- 2026-09-16: 관리 상세의 구조화 YAML은 raw JSON 대신 필드·chip·문장 목록·
  컬럼 행·SQL 예시로 표시한다. 최상위 빈 값은 명시하고 반복 컬럼의 선택적 빈
  필드는 생략한다.
- 2026-09-16: 우측 도구 상세에서 입력 JSON Schema를 숨긴다. Skills는 접기 버튼과
  raw Markdown을 제거하고 전체 절차를 의미 있는 제목·목록·코드로 표시한다.
  1280px 이상에서만 Inspector를 23rem으로 넓히며 Backend 계약은 유지한다.
  Frontend 67개 테스트·build·lint와 1280px/400px Workbench 회귀, 실제 API
  1440px 화면 검증을 통과했다. 기존 lint 13개·bundle 크기 경고는 남아 있다.
- 2026-09-16: 사용자 후속 요청으로 Skills의 disclosure를 복원한다. 이름·요약은
  항상 표시하고 선택한 상세만 펼치며, Markdown 가독성 개선과 API 계약은 유지한다.
  Frontend 67개 테스트·build·lint, Workbench 브라우저 9개와 실제 API의
  기본 접힘→펼침→재접힘·접근성 상태·overflow 검증을 통과했다.

## 구현 결정

- SDK tools/list의 실제 입력 스키마를 adapter에서 조회하고 TOOL_NAMES도 같은 등록 정의에서 파생한다.
- 검색은 async tool에서 worker thread로 실행해 SSE 이벤트 루프를 막지 않는다.
- 새 diagnostics가 포함된 initial_wip은 현업 재검토 전 draft로 되돌렸다. 원래 공식과 SQL은 유지한다.
- 채팅 영역은 크기를 유지해 숨기고 autoScroll을 중지한다. display:none으로 생기는 SDK 하단 추적 초기화 회귀를 브라우저 테스트로 고정했다.

## 검증 결과

Backend 기본 250개, 실제 provider 검색·인용 E2E 1개, Frontend 54개 및 build/lint 통과.
브라우저 대화 회귀 11개·관리 회귀 5개와 등록→인용 버전 열기 관통 검증 완료.
기존 lint 경고 13개·번들 크기 안내는 유지한다. Phase 3와 현업 지식 검토는 후속이다.
