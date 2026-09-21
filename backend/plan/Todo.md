# Production Planning Agent Backend 계획 및 이력

**상태: 진행 중. 마지막 갱신: 2026-09-21.**

이 문서는 Backend 작업의 목표, 현재 계약, 다음 작업과 완료 이력을 관리하는 단일
기준 문서다. 폐쇄망 반입 후 Backend workspace만 열어도 이해할 수 있도록 다른
workspace의 계획 문서를 전제로 하거나 링크하지 않는다.

## 목표와 책임

FastAPI와 Claude Agent SDK를 사용해 생산계획 데이터를 자연어로 조회·분석하고,
읽기 전용 SQL·입력 검증 simulation·지식 검색·표·차트 결과를 안정적인
`AgentEvent` SSE로 제공한다.

Backend가 소유하는 범위는 다음과 같다.

- API schema, SSE 변환, Agent 실행과 세션·포크·취소 lifecycle
- 구조화 YAML 및 버전형 텍스트 지식의 로드·검증·검색
- 읽기 전용 SQL 가드, mock/real service 경계와 simulation registry
- Result Store, 표 payload, 시각화 명세와 access scope·TTL
- 폐쇄망 실행·운영 문서, 오류 은닉과 service logging

운영 데이터 쓰기, 근거 없는 업무 수치 생성, 원시 chain-of-thought 공개는 범위
밖이다. 실제 사내 DB·RAG·simulation 연동은 아직 후속 작업이다.

## 현재 구현 상태

| 영역 | 상태 | 현재 기준 |
| --- | --- | --- |
| 채팅·Agent SSE | 완료 | `text`, `status`, `tool_call`, `tool_result`, `error`, `done`; delta 중복 제거, 안전한 종료·취소·포크 |
| Tool trace | 완료 | 동일 호출의 `tool_call_id`, 공개 가능한 args와 결과 연결 |
| 구조화 지식 | 완료 | table·KPI·recipe·scenario·simulation·glossary YAML 검증과 조회 Tool |
| 텍스트 지식 | 완료 | SQLite 버전·revision 충돌·검토·활성화·보관·local 검색 |
| SQL | Mock 완료 / Real 미구현 | 등록 table만 허용하는 SELECT/WITH, 1,000행 저장 상한 |
| Simulation | Mock 완료 / Real 미구현 | SMT2020 HVLM/LVHM 입력 관계·정합성 검증 |
| Result Store | 1차 완료 | parquet+metadata, TTL·용량 정리, browser access scope |
| 표 | 완료 | 검증된 결과에서 선택 컬럼과 최대 100행 payload |
| 시각화 | 완료 | 검증된 bar/line 명세, 최대 500 points·8 series |
| RAG | Local 완료 / Vector 미구현 | 활성 검토 문서 local 검색; Milvus·문서 색인 후속 |
| 실행 환경 | 완료 | Python 3.11 `.venv`, Backend 기본 포트 8100 |
| Service logging | 완료 | 공개 작업 시작·완료·실패, 소요 시간, 중첩 DEBUG와 민감정보 비노출 |

## 외부에 제공하는 안정 계약

상대 workspace 문서를 참조하지 않고 아래 계약을 Backend 자체 기준으로 유지한다.

### AgentEvent

- 안정 event type: `text`, `status`, `tool_call`, `tool_result`, `error`, `done`.
- 같은 Tool 호출은 안정적인 `tool_call_id`를 공유한다.
- `tool_call.data.args`에는 공개 가능한 모델 입력만 포함한다.
- 성공한 `done.data.turn_id`만 이후 포크 anchor로 사용한다.
- streaming 실패는 내부 예외를 숨긴 `error` 다음 terminal `done`을 보낸다.
- `thinking`, signature와 불완전 Tool JSON은 공개하지 않는다.

### 결과와 시각화

- `execute_sql`과 simulation 결과는 `result_id`로 Result Store에 저장한다.
- `prepare_table`은 scope·TTL·컬럼을 검증하고 최대 100행만 반환한다.
- `prepare_visualization`은 실제 결과 컬럼과 grain을 검증해
  `visualization_id`를 반환한다.
- 차트 조회는 `GET /api/visualizations/{visualization_id}`만 사용한다.
- 내부 파일 경로, access scope 값과 원본 대량 행은 Tool payload에 넣지 않는다.

### 지식과 SQL

- `knowledge/` YAML이 구조화 지식의 source of truth다.
- `query_rules`, `aggregation_rules`, `visualization_hints`의 역할을 섞지 않는다.
- table/recipe `sample_queries`는 `question`, `sql`만 허용한다.
- SQL은 항상 조회 전용이며 mock과 real 구현의 함수 시그니처·반환 형태를 맞춘다.

## 다음 작업

우선순위가 같은 항목은 업무 데이터와 폐쇄망 반입 준비 상황에 따라 조정한다.

### P1

- [ ] **SMT2020 외부 테스트 데이터셋 의존성 정리**: Git에 없는 원본·생성 DB·변환
  도구와 테스트 fixture의 경계를 문서화하고, 폐쇄망에서 재현 가능한 검증 경로를
  확정한다.
- [ ] **후속질문 동적 생성**: 성공한 `done`에 2~4개 제안을 선택적으로 추가한다.
  모델 출력 파싱 실패 시 빈 배열로 안전하게 종료하고 Fake/real 계약을 동일하게
  유지한다.

### P2

- [ ] 도메인 지식 관리 문서를 SMT2020 전용 설명에서 데이터셋 비종속 YAML 작성
  원칙 중심으로 일반화한다.
- [ ] 구조화 YAML과 향후 RAG가 함께 쓰는 `knowledge` 명칭을 정리한다. YAML의
  `domain` 전환 또는 RAG Tool의 `search_documents` 전환 중 하나를 호환성 범위와
  함께 결정한다.
- [ ] 실제 업무 데이터로 생산 부진 원인 scenario와 KPI·join·집계 정의를 현업
  검토하고 verified 상태를 갱신한다.
- [ ] 서버 처리 시간 공개 필요성, 측정 의미와 비용을 검토한다. 클라이언트 관측
  시간과 혼동되는 값은 추가하지 않는다.
- [ ] Result Store 후속 필터·재집계와 저장 backend 교체 필요성을 검토한다.

### P3

- [ ] 로컬 vector DB 기반 문서 색인·검색·출처 반환 RAG를 구현한다.
- [ ] `services/real`에 실제 사내 DB·RAG·simulation provider를 연결한다.
- [ ] 인증 principal, 영속 대화·분기 저장과 실제 모델 설정 조회 계약을 별도
  계획으로 설계한다.

## 완료 이력 요약

### 2026-09-08~14 — 기본 Agent와 도메인 지식

- FastAPI `/api/chat`, Claude Agent SDK adapter와 SSE `AgentEvent`를 구현했다.
- session/fork/cancel/error lifecycle과 Fake Runner를 마련했다.
- table·KPI·recipe·scenario·simulation·glossary 모델, 지식 Tool과 SQL 가드를
  구현했다. CTE, YAML `on` 파싱과 등록 table 검증 예외를 보강했다.

### 2026-09-15 — 결과·시각화·SMT2020와 안정화

- HVLM/LVHM을 `dataset` 업무 키로 구분하는 단일 SQLite mock 계약과 입력 관계
  검증을 구현했다.
- Result Store의 parquet/metadata, TTL·용량 정리와 결과 요약·구간 조회를
  구현했다.
- bar/line 시각화 명세 저장·조회, grain·숫자·series·point 검증을 구현했다.
- SDK 오류 은닉, 성공 turn anchor, access scope와 read-only SQL 회귀를 보강했다.

### 2026-09-16~18 — Tool UI 지원과 지식 관리

- delta streaming, Tool trace ID, standalone 표·차트 순서와 자동 표 보완 계약을
  구현했다.
- 표 100행, SQL 저장 1,000행 상한과 선택 catalog 인자 schema를 확정했다.
- 텍스트 지식 버전·검토·활성화 API와 local 검색, query/aggregation/visualization
  지식 규칙을 구현했다.
- Agent Workbench 감사용 오류·0행·빈 응답·미완료 fixture를 검증했다. 서버 timing,
  실제 모델과 대화 영속 저장은 의도적으로 보류했다.

### 2026-09-21 — 실행·운영 기준 정리

- 실행 환경을 Conda에서 Python 3.11 `.venv`로 통일하고 Backend 포트를 8100으로
  정리했다.
- `services` 공개 경계에 구조화 logging을 적용하고 입력·SQL·결과·경로·scope가
  로그에 노출되지 않도록 했다.
- 상세 날짜형 계획을 이 문서로 통합하고 Backend workspace 독립 계획 체계로
  전환했다.

## 검증 기준과 알려진 한계

- 기본 검증: `source .venv/bin/activate && python -m pytest -q`.
- 2026-09-21 통합 직전 기준: **269 passed, 6 deselected**, Starlette TestClient의
  upstream deprecation warning 1건.
- E2E는 실제 CLI/provider 인증이 있는 환경에서만 `python -m pytest -m e2e`로
  실행한다.
- 실제 provider 성공 응답, 실제 업무 데이터 정의와 폐쇄망 인프라 연결은 검증되지
  않았다.

## 계획 운영

- 작은 작업은 이 문서의 다음 작업·상태·완료 이력을 직접 갱신한다.
- 큰 작업만 같은 폴더에 `<yymmdd>-<topic>-plan.md`를 만들며 Backend 목표·계약·
  Task·검증을 문서 안에 완결한다.
- 다른 workspace 계획을 링크하거나 준비 상태를 추정하지 않는다. 필요한 외부
  API 조건은 이 문서 또는 활성 계획에 입력·출력·오류 형태로 직접 기록한다.
- 작업 완료 후 장기적으로 필요한 결정과 검증만 이 문서에 합치고 상세 실행 계획은
  제거해 이 폴더를 간결하게 유지한다.
