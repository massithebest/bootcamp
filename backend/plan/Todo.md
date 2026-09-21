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
- `ENV=prod`는 `SERVICE_MODE=real`과 bundled SMT2020 지식이 아닌 명시적인
  운영 `KNOWLEDGE_DIR`을 요구한다. 조건이 맞지 않으면 시작 단계에서 실패한다.

## 다음 작업

우선순위가 같은 항목은 업무 데이터와 폐쇄망 반입 준비 상황에 따라 조정한다.

### P1

- [ ] **후속질문 동적 생성**: 성공한 `done`에 2~4개 제안을 선택적으로 추가한다.
  모델 출력 파싱 실패 시 빈 배열로 안전하게 종료한다.

### P2

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
- session/fork/cancel/error lifecycle과 임시 Fake Runner를 마련했다(2026-09-21
  제거, 아래 참고).
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
- SMT2020 원본·생성 DB·변환 도구를 개발용 mock 회귀 자산으로 한정했다. 자산이
  없는 환경에서는 관련 테스트만 skip하며, 폐쇄망은 prod/real/별도 운영 지식을
  fail-fast 계약으로 강제한다.
- 도메인 지식 관리 문서의 테이블·KPI·recipe·scenario 작성 원칙과 예시를
  SMT2020 고유 값(HVLM/LVHM, wip 등) 대신 `segment_key` 같은 데이터셋 비종속
  placeholder로 바꿨다. SMT2020 관련 설명은 "개발용 SMT2020 데이터와 검증",
  "SMT2020 진단 범위" 절에만 남겼다.
- 번들 SMT2020 지식의 고정 값을 단정하는 테스트를 `smt2020_bundle` 마커와
  `bundled_knowledge` fixture로 분리했다. 운영 지식 디렉터리를 붙이거나 `knowledge/`
  내용을 교체해도 마커 제외 프로필이 통과한다. 일반 정합성 테스트의 "KPI 1건 이상"
  기대는 제거했다.
- `knowledge` 명칭 충돌은 RAG Tool을 `search_knowledge`에서 `search_documents`로
  바꿔 해소했다. 호환성 범위는 Tool 이름(Agent 지시문·Skill 표·SDK 등록·이벤트의
  `tool_name`)뿐이며, 결과 `kind: "knowledge"`, `/api/knowledge/*`, 환경변수,
  `knowledge/` YAML 경로는 유지한다. 옛 Tool 이름의 별칭은 두지 않는다.
- Fake Runner와 `PLANNING_AGENT_FAKE`를 제거했다. `/api/chat`은 항상 Claude Agent
  SDK 경로를 사용하며 테스트는 SDK `query`나 `run_agent`를 대체해 이벤트 계약을
  검증한다. 지식·시각화 API와 `pytest`는 provider 없이 동작한다.
- 문서 전체를 코드와 대조해 Fake Runner 실행 안내를 제거하고, 폐쇄망 최소 설정에
  `KNOWLEDGE_DB_PATH`·`KNOWLEDGE_SEARCH_BACKEND`·`CORS_ALLOW_ORIGINS`와 텍스트 지식
  SQLite 영속화 확인 항목을 추가했다.
- `active: false` 구조화 지식이 Agent 경로에서 실행·노출되지 않게 했다.
  `validate_simulation_request`가 비활성 simulation을 거부하고, 활성 항목의 join
  대상·`recipe_refs`·diagnostics·`follows`·용어집 `related_*` 참조 중 비활성
  항목은 조회 결과에서 제외한다. 관리 화면 목록은 비활성도 그대로 보여준다.
  원천 `sources`에 비활성 table이 있는 KPI·recipe도 목록에서 제외하고 상세 조회는
  원인을 담은 오류를 반환한다(관리 화면은 파생 상태를 표시하지 않음).
- Simulation YAML에 선택 필드 `aggregation_rules`, `visualization_hints`를 추가했다
  (생략 시 빈 목록). `list_simulation`·`/api/knowledge/entries` 상세 응답에 포함된다.

## 검증 기준과 알려진 한계

- 기본 검증: `source .venv/bin/activate && python -m pytest -q`.
- 2026-09-21 기준 전체 개발 검증: **285 passed, 6 deselected**. SMT2020 자산을
  제외한 clean 복사본은 **244 passed, 41 skipped, 6 deselected**다. 마커 제외
  프로필(`not smt2020 and not smt2020_bundle and not mock_service and not e2e`)은
  **223 passed, 68 deselected**다.
- 세 검증 모두 Starlette TestClient의 upstream deprecation warning 1건만 남는다.
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
