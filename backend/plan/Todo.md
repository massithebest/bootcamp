# Production Planning Agent Backend 계획 및 이력

**상태: 진행 중. 마지막 갱신: 2026-09-28.**

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
- 읽기 전용 SQL 가드, mock/production service 경계와 simulation registry
- Result Store, 표 payload, 시각화 명세와 access scope·TTL
- 폐쇄망 실행·운영 문서, 오류 은닉과 service logging

운영 데이터 쓰기와 근거 없는 업무 수치 생성은 범위 밖이다. 모델 thinking(chain-of-thought)은
어떤 경우에도 공개하지 않는다. 실제 사내 DB·RAG·simulation 연동은 아직 후속 작업이다.

## 현재 구현 상태

| 영역 | 상태 | 현재 기준 |
| --- | --- | --- |
| 채팅·Agent SSE | 완료 | `text`, `status`, `tool_call`, `tool_result`, `error`, `done`; delta 중복 제거, 안전한 종료·취소·포크 |
| Tool trace | 완료 | 동일 호출의 `tool_call_id`, 공개 가능한 args와 결과 연결 |
| 구조화 지식 | 완료 | table·KPI·recipe·scenario·simulation·glossary YAML 검증과 조회 Tool |
| 텍스트 지식 | 완료 | SQLite 버전·revision 충돌·검토·활성화·보관·local 검색 |
| 구조화 지식 변경·승인 | 완료 | 변경 요청(초안·제출·승인·반려)·정합성 게이트·승인 시 YAML 원자 반영·즉시 reload, principal 스텁 |
| SQL | Mock 완료 / Production stub | 등록 table만 허용하는 SELECT/WITH, 1,000행 저장 상한 |
| Simulation | Mock 완료 / Production stub | 합성 mock SEG_A/SEG_B 입력 관계·정합성 검증 |
| Result Store | 1차 완료 | parquet+metadata, TTL·용량 정리, browser access scope |
| 결과 API·표·시각화 | 완료 | `/api/query-results/{id}/preview|table|chart`, `present_sql_preview`·`present_chart`·`present_table`·`present_simulation` flat Tool·검증(유일한 결과 표시 경로, 최대 500 points·8 series) |
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
- 모델 thinking(`ThinkingBlock`), signature와 불완전 Tool JSON은 공개하지 않는다.

### 결과와 시각화

- `execute_sql`과 simulation 결과는 `result_id`로 Result Store에 저장한다.
- 내부 파일 경로, access scope 값과 원본 대량 행은 Tool payload에 넣지 않는다.
- `execute_sql`·`run_simulation`은 bounded preview(`result_id`, `row_count`,
  `source_truncated`, `columns`, `sample_rows`(≤5, 객체), `date_ranges`, `distinct_counts`, `statistics`,
  `top_groups`(컬럼당 ≤10); simulation은 `simulation_type`·`scenario`·`summary`·`kpis`; SQL은 `purpose`만)만 반환하고,
  flat(스칼라 인자) Tool 4개를 등록한다: `present_sql_preview(sql, title?)`,
  `present_chart(result_id, chart_type, x_column, y_column, group_by_column?, aggregation?, title?)`,
  `present_table(result_id, columns?, title?)`, `present_simulation(scenario, summary, kpis, result_id?)`.
  (과거에는 `present` tool 하나가 UI 트리 전체를 `tree` JSON-문자열 하나로 받았으나, 실제
  tool-calling 모델이 문자열 타입을 지키지 못해 Claude Agent SDK의 강제 `jsonschema.validate`에
  막혀 `is_error=True`로 반복 실패하는 문제(2026-09-22 확인·재현)가 있어 이중 인코딩 자체를
  없앴다. `resultId`·chart 설정을 실제 결과로 재검증하고, 성공 `{}`/실패
  `{status:"error", code, message, details.path}`를 반환하는 계약은 그대로다. 여러 결과를
  한 화면에 시각적으로 묶는 기능(과거 `Card`)은 없다 — 같은 `result_id`로 여러 `present_*`를
  호출해도 화면에는 순차적으로 나열되며 연결은 모델이 텍스트로 설명한다. 자동 표 보완은
  하지 않는다.
- `GET /api/query-results/{result_id}/preview|table|chart`(같은 `pp_session_scope`): table `page`·`page_size`(기본 10, ≤100)·
  `columns`·`search`(≤200)·`sort_column`·`sort_direction(asc|desc)`를 저장된 최대 1,000건 전체에 적용하고
  `row_count`·`filtered_row_count`와 현재 page를 반환한다. chart는 `chart_type(bar|line|area)`·`x_column`·`y_column`·
  `group_by_column`·`aggregation(sum|avg|count|min|max)`·`title`.
  없음·만료·타 scope는 404 `RESULT_NOT_FOUND`(동일 응답), 422 `INVALID_REQUEST`·`COLUMN_NOT_FOUND`·`INVALID_COLUMN_ROLE`·
  `AGGREGATION_REQUIRED`·`EMPTY_RESULT`·`UNRENDERABLE_VALUES`. chart는 series ≤8(초과 시 상위만+`SERIES_LIMITED`),
  point ≤500(시계열은 `TIME_BUCKETED`, 범주는 `CATEGORIES_LIMITED`; 시계열 재집계는 aggregation 필요).

### 지식과 SQL

- 실행 중인 `KNOWLEDGE_DIR` YAML이 구조화 지식의 source of truth다. 개발 기본은
  `knowledge/mock/`, 폐쇄망 반입 기본 위치는 `knowledge/production/`이다.
- `query_rules`, `aggregation_rules`, `visualization_hints`의 역할을 섞지 않는다.
- table/recipe `sample_queries`는 `question`, `sql`만 허용한다.
- SQL은 항상 조회 전용이며 mock과 production 구현의 함수 시그니처·반환 형태를 맞춘다.
- `ENV=prod`는 `SERVICE_MODE=production`(기존 `real` 별칭 허용)과 bundled mock 지식이 아닌 명시적인
  운영 `KNOWLEDGE_DIR`을 요구한다. 조건이 맞지 않으면 시작 단계에서 실패한다.

### 구조화 지식 변경 요청·승인

구조화 YAML은 직접 수정 API가 없고 변경 요청이 승인될 때만 파일이 바뀐다. 상세 절차와
운영 전제는 `docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md`의 "구조화 지식 변경 요청과 승인"이 기준이다.

- 권한: 요청마다 `X-User-Id`(생략 시 `KNOWLEDGE_DEFAULT_PRINCIPAL`)를 `KNOWLEDGE_PRINCIPALS`와
  대조한다. 권한은 `knowledge:write`(작성·제출·철회), `knowledge:approve`(승인·반려)다.
  알 수 없는 id·권한 부족·`KNOWLEDGE_MANAGEMENT_ENABLED=false`는 403 `{"detail"}`이다.
  스텁은 보안 경계가 아니며 실제 인증이 오면 `core/principal.py::current_principal`만 바꾼다.
- `GET /api/me` → `{id, name, permissions[], mode: "stub"|"authenticated",
  knowledge_management, allow_self_approval, stub_users[{id,name}]}`. `stub_users`는 스텁에서만 채운다.
- `GET /api/knowledge/guides/{kind}` → `{kind, key_field, fields[], template, immutable[]}`.
  `fields[]`는 `{name, path, label, help, required, readonly, widget, example?, group?,
  options?, item_widget?, fields?, value?}`이며 widget은 string·text·sql·boolean·number·date·enum·
  string_list·record_list·object·map·json이다. 구조는 pydantic 모델, 문구는
  `services/knowledge/guides.py`가 소유한다. `item_widget`(string|text)은 string_list 항목이 여러 줄 입력이 필요한지 알린다.
  `template`은 필수 필드만 빈 값으로 채운 골격이다.
- `GET /api/knowledge/source/{kind}/{key}` → `{kind, key, yaml, data}` 현재 항목의 정규화 내용(404).
- `POST /api/knowledge/validate` `{kind, key?, yaml|data}` → 200 `{ok, parsed, yaml, data, key,
  errors[{path, line, message}]}`. `yaml`(원문)과 `data`(폼) 중 정확히 하나만 보낸다.
  `key`가 있으면 기존 항목 수정으로 보고 식별자 변경을 막는다. `parsed`는 입력이 mapping으로
  읽혔는지이며 `data` 입력이 모델 검증에 실패해도 원문 탭용 `yaml`을 돌려준다. 저장하지 않는다.
- `GET /api/knowledge/changes?state=&kind=&mine=` → 요약 목록
  `{id, kind, key, is_new, state, revision, author{id,name}, created_at, updated_at}`.
- `POST /api/knowledge/changes` `{kind, key?, yaml|data}` → 201 상세. `key` 없으면 신규 항목.
  `GET /changes/{id}` 상세는 요약에 `yaml, data, current_yaml, history[]`를 더한다.
  history: `{revision, action, actor_id, actor_name, note, self_approved, at}`,
  action은 create·save·submit·withdraw·approve·reject.
- `PUT /changes/{id}` `{expected_revision, yaml|data}`, `POST /changes/{id}/{submit|withdraw|
  approve|reject}` `{expected_revision, note}`. approve·reject는 `knowledge:approve`와 note가 필요하다.
- 오류: 403 권한·작성자 아님·자기 승인, 404, 409 revision 충돌·진행 중 요청 존재·기준 변경·
  상태 불일치·이미 있는 키, 422 검증 실패, 503 저장소·반영 실패(경로 미노출).
- `GET /api/knowledge/entries`는 scenario를 포함하고 각 행에 `pending_change{id,state}|null`을 더한다.

## 다음 작업


### P1

- [ ] **후속질문 동적 생성**: 성공한 `done`에 2~4개 제안을 선택적으로 추가한다.
  각 제안은 1~120자, 중복·빈 문자열 없이 한국어 질문 문구로 제한한다. 데이터에
  종속된 답이나 비공개 추론은 생성하지 않는다. 파싱·생성 실패는 응답 전체를 실패시키지
  않고 `suggestions`를 생략하거나 빈 배열로 종료한다. 오류·취소 turn에는 붙이지 않는다.
  소비자 파서는 이미 준비돼 있다.

### P2

- [ ] 실제 업무 데이터로 생산 부진 원인 scenario와 KPI·join·집계 정의를 현업
  검토하고 verified 상태를 갱신한다.
- [ ] 서버 처리 시간 공개 필요성, 측정 의미와 비용을 검토한다. 클라이언트 관측
  시간과 혼동되는 값은 추가하지 않는다.
- [ ] Result Store 후속 재집계와 저장 backend 교체 필요성을 검토한다.

### P3

- [ ] 로컬 vector DB 기반 문서 색인·검색·출처 반환 RAG를 구현한다.
- [ ] `services/production`에 실제 사내 DB·RAG·simulation provider를 연결한다.
  인터페이스·설정 가드레일(`common_sql_client.py`·`milvus_client.py`·
  `simulation_api_client.py` 스텁과 env var 자리는 선행 준비를 마쳤다(2026-09-23).
  `/anthropic` 경로와 `LLM_PROVIDER=local` 설정은 유지하되 프록시 본문은 비워
  두었으며, 폐쇄망에서 사용할 구현을 반입한 뒤 채운다. 남은 작업은 실제 pntfp
  HTTP 호출 로직 이식이다.
- [ ] 실제 폐쇄망 DB 스키마·RAG 문서 구조 정보를 확보하면
  `scripts/generate_mock_database.py`의 `SEGMENTS`(세그먼트 규모)와
  `scripts/generate_mock_documents.py`의 문서 주제·카테고리를 재검토해 실제
  구조와의 유사도를 높인다. 테이블/컬럼명은 실제 스키마가 크게 다르면 그때
  다시 정한다.
- [ ] 인증 principal, 영속 대화·분기 저장과 실제 모델 설정 조회 계약을 별도
  계획으로 설계한다. 착수 전 실제 인증 principal과 폐쇄망에 반입 가능한 저장소를
  정하고, 소유권·재시작 후 fork·보존 기간·24시간 Result Store TTL이 지난 결과 참조의
  표시 정책을 함께 결정한다. 현재 임시 principal을 보안 경계로 사용하지 않는다.

## 완료 이력 요약

### 2026-09-28 — mock·production 구조화 지식 분리

- 기존 번들 YAML을 `knowledge/mock/`으로 이전하고 개발 기본 `KNOWLEDGE_DIR`을 그
  경로로 변경했다. 폐쇄망 실제 YAML은 `knowledge/production/`에 추가해 명시적으로
  지정하며, prod는 mock 또는 지식 상위 디렉터리를 거부한다.
- 폐쇄망 이식 가이드에 production YAML 디렉터리 구조, Windows 환경변수 설정과
  mock YAML 비반입 원칙을 추가했다.

### 2026-09-26 — 계약 유지 리팩토링과 지식 모델 분리

- 공유 계약을 대조해 공개 AgentEvent 6종과 `present_*` 인자의 타입·필수 여부·enum·
  길이/개수 제한이 소비자 fixture와 일치함을 확인했다. API·Tool·오류 의미는 유지한다.
- `services/knowledge/models.py`로 Pydantic 모델과 `KindSpec`·`KIND_SPECS`를 옮겼다.
  `catalog.py`는 YAML 로딩·조회·store cache를 담당하며 기존 모델 import를 재노출한다.
  guides·changes는 모델 registry만, writer는 registry와 catalog 저장소를 각각 참조한다.
  승인·reload·로그·비활성 지식 필터와 SQL 허용 테이블 계약은 유지한다.
- 기준/최종 검증: `python -m pytest -q` **378 passed, 6 deselected**,
  `python -m pip check` 정상. 실제 provider E2E는 실행하지 않았다.
- 남은 경고: Starlette TestClient의 AnyIO alias deprecation 1건(upstream).


### 2026-09-23 — PKT 목표수량 Swap knowledge 반영과 mock 시뮬레이션

- 사용자가 제공한 실제 사내 "PNS PNT-FP API"(PktTarget swap 산출) 스펙을 근거로
  `knowledge/mock/simulations/PKT_목표수량_스왑산출.yaml`을 새 simulation_type으로
  등록했다. `view`(all/swapped/by_ids)와 `plan_prod_ids`(by_ids일 때만 필요) 파라미터를
  갖는다. `glossary.yaml`에 "PKT 목표수량 Swap"·"Swap 우선순위 정책" 용어를 draft로
  추가했다 — 기존 `VUI_FP_TARGET_I`(배치 반영 이력)와는 별개 원천임을 명시했다.
- `services/mock/mock_pkt_swap.py`(신규)에 고정 seed 기반 합성 데이터로 `targetQty =
  planQty - poutQty` 계산과 우선순위 기반 근사 GIVE/RECEIVE swap을 재현하는
  `generate_pkt_swap_response(view, plan_prod_ids)`를 구현했다.
  `services/mock/mock_simulation_service.py`가 기존 `run_simulation` Tool 경로로 이
  simulation_type을 그대로 처리하도록 분기를 추가했다(새 SDK Tool 없음).
- 폐쇄망 실제 REST 연동(`services/production/*.py`)은 범위 밖으로 남겼다 — 폐쇄망
  접근 없이는 검증할 수 없으므로 기존 `NotImplementedError` 스텁 그대로 두었고, 이번에
  확보한 실제 API 스펙은 `docs/CLOSED_NETWORK_SETUP.md` Part 2 이식 작업 때 참고한다.
  Product/ProductAssignment/Configuration(swap-priority 조회) 엔드포인트는 별도
  Tool로 만들지 않고 PKT swap mock 계산용 내부 합성 데이터로만 반영했다.
- 검증: `python -m pytest -q` **377 passed, 6 deselected**.

### 2026-09-23 — 도메인 지식 관리 문서 파일명 대문자화

- 도메인 지식 관리 문서 이름을 대문자로 변경하고 README·계획·코드 주석의
  참조를 갱신했다.
- 앞으로 `docs/`에 작성하는 문서 파일명은 대문자로 쓰도록 root 및 Backend
  `AGENTS.md` 지침에 추가했다.

### 2026-09-23 — `/anthropic` 프록시 구현을 폐쇄망 반입 대상으로 전환

- 사용자 지시에 따라 오픈망 작업본의 게이트웨이 전달 구현을 제거하고,
  `/anthropic/{path}` 경로는 유지하면서 반입 전 요청에 501을 반환하도록 했다.
- `LLM_PROVIDER=local` 설정은 유지했다. 폐쇄망 구현을 반입하기 전에는 이 설정으로
  Agent 요청을 처리할 수 없다.
- 기존 전달 테스트와 폐쇄망 안내를 미구현 상태에 맞게 갱신했다.

### 2026-09-23 — pntfp 반입 대비 사전 준비(`/anthropic` 프록시·production 가드레일·missing_params, 이후 프록시 501 전환)

- 다음 폐쇄망 pntfp 반입 때 오픈망에서 미리 끝낼 수 있는 작업만 골라
  구현했다. 실제 사내 API 스펙(엔드포인트·스키마)이 없는 부분은 인터페이스와
  설정 가드레일까지만 만들고 `NotImplementedError`로 남겼다.
- 당시 `/anthropic` 프록시(`api/routes_anthropic_proxy.py`)와 `LLM_PROVIDER=local`
  분기(`core/config.py::agent_provider_env`)를 구현했다 — 사내 LLM
  게이트웨이(HCP)가 Claude CLI User-Agent를 차단하는 문제를, CLI 요청을
  백엔드 자신의 `/anthropic/*`로 보내 User-Agent만 교체해 전달하는 방식으로
  우회하는 방식이었다. `BACKEND_PORT`, `PRIVATE_LLM_MODEL_NAME/ENDPOINT/KEY` 설정을
  추가했다. 당시 로컬 mock 게이트웨이로 스트리밍·헤더 교체·인증 전달을 수동 검증했으나,
  전달 본문은 위의 501 전환에서 제거했다.
- `services/production/{common_sql_client,milvus_client,simulation_api_client}.py`
  스텁을 추가하고, `COMMON_SQL_API_URL`/`SIMULATION_API_URL`/`MILVUS_*`/
  `IFLOW_EMBEDDING_*`/`RERANKER_*`/`RAG_DOC_URL_BASE` env var 자리와
  `core.config.require_production_env` 호출 시점 가드레일을 마련했다. 실제
  HTTP 로직은 이식 대상으로 `docs/CLOSED_NETWORK_SETUP.md` §2-4를 가리키는
  TODO만 남겼다.
- `services/simulation/registry.py::validate_simulation_request`가 문자열
  대신 구조화 dict를 반환하도록 바꿨다 — 필수 파라미터가 없으면
  `{"status": "missing_params", "missing": [...]}`을 반환해 agent가 추측
  재시도 대신 사용자에게 직접 되묻는다. mock/production `simulation_service`와
  `simulation` Skill 4단계를 함께 갱신했다.
- `tests/test_real_services.py`(신규)에 production 어댑터 설정 가드레일,
  `missing_params` 구조화 응답 테스트를 추가했다. 프록시 전달 테스트는 위의
  501 전환에서 미구현 응답 테스트로 교체했다. 이식 후에는 같은 파일에 SQL/RAG/simulation
  성공 경로 테스트를 더한다.
- `.gitignore`에 `/backend/pntfp/`를 추가하고, `docs/CLOSED_NETWORK_SETUP.md`에
  `/anthropic` 프록시 사용법과 Milvus 컬렉션 스키마 대조·시뮬레이션 API 응답
  대조·프록시 스트리밍 검증을 이식 후 검증 절차에 추가했다.
- 검증: `python -m pytest -q` **372 passed, 6 deselected**.
- 미수행: 실제 pntfp HTTP 호출 로직(SQL/RAG/simulation 성공 경로), 실제
  Milvus/Simulation API 응답 스키마 대조, 사내 게이트웨이 실환경에서의
  `/anthropic` 프록시 관통 검증(로컬 mock 게이트웨이로만 확인함).

### 2026-09-23 — Production API timeout 설정 추가

- `.env`와 `.env.example`에 `API_TIMEOUT_SECONDS=60`을 설정하고 `core.config`에서 정수 초 단위로 읽도록 했다.
- 폐쇄망 production adapter가 사용할 설정으로 README와 폐쇄망 가이드에 기록했다. 현재 API 호출부는 아직 연결되지 않아 설정값만 준비했다.

### 2026-09-23 — 사용자 의도에 따른 SQL·simulation·문서 검색 경로 안내

- `agent/agent_sdk/CLAUDE.md`에 질의 경로 표를 추가했다. "시뮬레이션 수행/실행"은 등록 simulation 확인·실행으로, "DB/데이터베이스/SQL 조회"는 읽기 전용 SQL로, 정의·버튼·변경 위치·방법 질문은 문서 검색으로 연결한다. "알려줘/보여줘" 같은 말투는 경로 판별 기준에서 제외한다.
- 직전 결과를 가리키는 후속 질문은 성공한 Tool 출처와 `result_id`를 이어받도록 했고, 대상·결과가 불명확하면 확인한다. 등록되지 않은 simulation은 임의 실행이나 SQL 결과로 대체하지 않고 미지원으로 안내한다.
- SQL·simulation Skill과 세 Tool 설명에도 같은 기준을 반영했다. API·AgentEvent·Tool payload 계약은 변경하지 않았다.
- `test_prompt_consistency.py`에 경로 정책과 Tool 설명의 일치 검사를 추가했다. 전체 Backend 테스트 **362 passed, 6 deselected**로 검증했다(Starlette TestClient deprecation warning 1건).

### 2026-09-23 — Backend service 패키지 구조화와 production 명칭 정리

- 지식 서비스는 `services/knowledge/`, 결과 처리는 `services/results/`, SQL guard는
  `services/sql/guard.py`, 공통 simulation schema는 `services/simulation/`으로 묶었다.
- `services/real/`을 `services/production/`으로 옮겼다. `SERVICE_MODE=production`을
  표준으로 하고 기존 `SERVICE_MODE=real` 입력은 호환 별칭으로 정규화한다.
- mock/production public API, HTTP·Tool payload 계약은 유지한다. 각 패키지의 import와
  회귀 테스트·폐쇄망 문서를 새 경로에 맞췄다. 전체 Backend 검증은 360 passed,
  6 deselected로 완료했다.


### 2026-09-23 — SMT2020/rag_docs 의존성을 합성 mock 생성기로 교체

- `backend/datasets/`(SMT2020 원본 TSV, 생성 DB, 반도체 rag_docs)와
  `backend/scripts/build_smt2020_db.py`·`seed_local_documents.py`(둘 다 Git
  비추적)를 삭제했다. 대신 외부 원본 없이 결정적(seed 고정)으로 합성 데이터를
  만드는 `scripts/generate_mock_database.py`·`generate_mock_documents.py`를
  추가했다 — 실제 데이터를 다루지 않는 순수 코드이므로 Git에 포함시켜 어떤
  환경에서도 실행 가능하다.
- 테이블·컬럼 스키마(`part`/`route_step`/`tool`/`orders`/`wip`/`setup`/
  `setup_group`/`down_calendar`/`pm_calendar`/`calendar_attach`/`transport`)는
  그대로 유지해 `knowledge/mock/catalog/`·`sql_guard`·mock SQL/simulation service를
  바꾸지 않았다. `dataset` 값만 `HVLM`/`LVHM` → `SEG_A`/`SEG_B`로 중립화했고,
  `core.config.SMT2020_DB_PATH` → `MOCK_DB_PATH`(기본 경로
  `backend/data/mock_planning.db`), `Smt2020DbMissingError` →
  `MockDbMissingError`, simulation type `SMT2020_입력검증` →
  `입력_정합성_검증`으로 이름을 바꿨다.
- `knowledge/` YAML 전체(11개 table, joins, glossary, kpi, recipes 3종,
  simulations, scenarios 2종)에서 SMT2020/HVLM/LVHM 리터럴을 제거하고
  scenario 파일도 `seg_a_input_integrity.yaml`/`seg_b_input_integrity.yaml`로
  옮겼다. RAG mock 문서는 반도체 용어집 대신 일반 생산계획 용어집(Route·WIP·
  Setup·Downtime/PM Calendar·Transport·Lot·Tool Capacity·세그먼트 전략) 9건으로
  교체했다.
- `pytest.ini`의 `smt2020`/`smt2020_bundle` 마커(자산 유무에 따른 skip 목적)를
  없앴다 — 생성기가 항상 Git에 있어 더 이상 skip이 필요 없다. `mock_service`는
  유지하고 `smt2020_bundle`은 `bundled_knowledge`로 이름을 바꿨다(기능은 동일).
  `tests/test_smt2020_dataset.py`를 `test_mock_database.py`로 옮기고 TSV 파싱
  전용이던 두 테스트(padding, header 오류)를 새 생성기에 맞는 형태로 교체했다.
- 검증: `python -m pytest -q` **359 passed, 6 deselected**(e2e만 제외).
  `python -m scripts.generate_mock_database`·`generate_mock_documents` 수동
  실행과 5개 입력 관계 unmatched=0, `PRAGMA integrity_check=ok`, 두 번 빌드
  결과 동일함(결정적 재현성)을 확인했다.
- 미수행: 실제 폐쇄망 DB 스키마·RAG 문서 구조 정보 반영(위 P3 참고). 현재
  세그먼트 규모·컬럼은 기존 SMT2020 값을 그대로 복제한 placeholder다.

### 2026-09-23 — Result Store·SSE·RAG 경계 보강

- Result Store 읽기는 검증된 `result_id`로 파일 경로를 계산하고 sidecar ID 불일치를
  거부한다. API의 scope·TTL 검사는 공통화하되 저장 형식과 Tool의 과거 unscoped
  결과 허용 정책은 유지한다.
- Chat SSE 예외 경로는 `AgentEvent`로 직렬화하고 예외 클래스만 기록해 내부 메시지를
  노출하지 않는다. RAG Tool은 Service 경계를 사용하며 local 검색 선택은
  `SERVICE_MODE`와 독립적으로 유지한다.
- 오래된 assistant-ui 상세 계획은 제거하고 남은 후속질문·대화 영속 검토를 이 문서의
  P1/P3에 통합했다.
- 검증: 전체 **360 passed, 6 deselected**. Starlette 의존성 deprecation warning 1건.

### 2026-09-23 — assistant-ui 통합 상세 계획 정리

- 완료된 Result API·flat `present_*`·legacy 제거 단계와 현재 계약은 이 문서가 기준이다.
  이전 실행 계획의 남은 제안은 P1 후속질문과 P3 인증·대화 영속 설계에 통합했다.
- 이전 상세 계획은 `RESULT_UI_MODE`, legacy 롤백, 단일 `present` Tool을 현재 지침처럼
  서술해 더 이상 유지하지 않는다. 후속질문과 대화 영속은 별도 작업으로 남긴다.

### 2026-09-22 — legacy 결과 표시 모드 삭제

- `RESULT_UI_MODE` 플래그와 `legacy` 모드(`prepare_table`·`prepare_visualization` Tool,
  `GET /api/visualizations/{id}`, 자동 표 보완, `services/table_service.py`·
  `visualization_service.py`·`visualization_store.py`·`visualization_models.py`,
  `tools/table_tool.py`·`visualization_tool.py`)를 통째로 삭제했다. 결과 표시는 이제
  `present_*` flat Tool과 `/api/query-results/*`만 사용하는 단일 경로다.
- 사용자 결정으로 원래 계획했던 "실제 provider 관찰 후 기본값 전환" 관찰 게이트를
  건너뛰고 바로 legacy를 제거했다 — `present` 모드는 이미 실제 provider(OpenRouter
  GLM-5.3-flash)로 검증됐고 legacy를 유지할 이유가 없다고 판단했다.
- `agent/agent_sdk_present/`를 `agent/agent_sdk/`로 옮겨 유일한 런타임 지침
  디렉터리로 만들었다. `agent.py`의 `agent_sdk_cwd(mode)`/`AGENT_SDK_PRESENT_CWD`,
  `sdk_tools.py`의 `mode` 매개변수(`planning_tools`·`tool_names`·
  `build_planning_mcp_server`·`tool_catalog`)를 제거하고 두 값 중 하나를 고르던
  분기를 없앴다. `agent.py`의 표 자동 보완(`_needs_table_fallback` 등)도 함께
  삭제했다.
- `services/mock/mock_sql_service.py`·`mock_simulation_service.py`가 `result_ui_mode()`로
  갈라졌던 legacy/`present` 분기를 없애고 항상 `tool_preview`(bounded preview)만
  반환하도록 정리했다. `chart_projection.py`가 `visualization_service.py`에서 가져오던
  `_json_value`·`_identity`·`_time_key`·`_label_column` 헬퍼는 `chart_projection.py`
  자체로 옮겨 의존을 끊었다.
- `test_prompt_consistency.py`(legacy)와 `test_prompt_consistency_present.py`를 하나로
  합쳐 `test_prompt_consistency.py`로 재작성했다(두 디렉터리를 비교하던 로직 삭제,
  단일 디렉터리 기준 검증만 유지). `test_result_ui_mode.py`는 삭제하고 남길 가치가
  있는 assertion은 `test_services.py`·`test_event_adapter.py`로 옮겼다.
- 검증: `python -m pytest -q` 354 passed, 6 deselected (자세한 내역은 아래
  "검증 기준과 알려진 한계" 참고).

### 2026-09-22 — 개발 문서 역할 정리

- `AGENTS.md`는 Backend 경계·공유 계약·검증만 남기고 세부 구현 설명을 계획과
  운영 문서로 돌렸다. 개발용 `CLAUDE.md`는 `AGENTS.md` 호환 진입점으로 유지했다.
- 런타임 `agent_sdk*/CLAUDE.md`는 Tool·Skill 인덱스와 공통 안전 규칙만 남기고
  업무 절차는 Skills, schema는 Tool 설명을 기준으로 하도록 축약했다.
- Backend README의 `present` 모드를 현재 flat `present_*` Tool 계약에 맞췄다.

### 2026-09-22 — 결과 API·`present` Tool·플래그

- 저장 없는 preview·table·chart API(`services/results/query.py`, `chart_projection.py`)와 `present` Tool
  (`services/results/present.py`, `tools/present_tool.py`), 플래그 `RESULT_UI_MODE`(기본 `legacy`)를 구현했다.
- `present` vocabulary는 여러 결과를 묶는 `Card`와 도메인 `SqlPreview`·`QueryChart`·`QueryTable`·
  `SimulationSummary`만 허용한다. 일반 설명·상태·경고는 공개 답변 text 또는 검증된 도메인 UI가 담당한다.
  `present` 모드는 preview-only payload, Tool 집합 교체, 자동 표 보완 제거, `agent/agent_sdk_present/` 지침을 함께 전환한다.
- Claude Code가 `$`로 시작하는 property 이름을 Tool schema에서 제외하는 문제와 실 provider 관통
  검증에서 재귀 `$ref` schema가
  `children`을 JSON 문자열로 변형하고 root `component`를 누락하는 것을 확인해, Tool 자체는
  `tree` JSON 문자열 하나만 받도록 보강했다. 문자열 안에서는 assistant-ui 표준
  `$type`/`$key`를 그대로 쓰고 Backend가 파싱·검증해 AgentEvent에 싣는다.
- 검증: `pytest -q` 423 passed, 6 deselected. 실제 provider의 SQL→`present` 관통 호출은
  한 번에 성공했고 공개 SSE에는 canonical `$type` 트리와 빈 성공 결과가 전달되며 본문에 raw JSON이 섞이지 않았다.
  legacy 동작·기존 API는 회귀 테스트로 유지한다.
- 미수행: simulation→`present` 실제 provider e2e, 운영 기본값 결정, 후속질문 필드
  (`done.data.suggestions`), 대화·분기 영속 API.

### 2026-09-22 — `present` Tool을 flat `present_*` 4개로 재설계

- 실제 운영 provider가 Claude가 아니라 OpenRouter의 `z-ai/glm-5.3-flash`임을 확인했다. 위
  항목에서 만든 `tree` JSON-문자열 이중 인코딩을 이 모델이 자주 어기고 `tree`를 객체 그대로
  보내, Claude Agent SDK의 강제 `jsonschema.validate`(`claude_agent_sdk/types.py`의 `run_tool`)가
  Python 코드 실행 전에 `Input validation error: ... is not of type 'string'`로 호출을 거부하는
  것을 직접 재현해 확인했다. MCP는 이 SDK(0.2.152)에서 custom tool 등록의 유일한 경로이고
  이 강제 검증도 끌 수 없어(비-MCP 우회 불가), 이중 인코딩 자체를 없애는 재설계로 해결했다.
- `present` 하나를 `present_sql_preview`·`present_chart`·`present_table`·`present_simulation`
  4개 flat Tool로 교체했다(`services/results/present.py`, `tools/present_tool.py`,
  `agent/sdk_tools.py`). `VOCABULARY`·`present_input_schema`·`decode_present_input`·
  `to_assistant_ui_tree`·`_walk`(재귀 검증)를 삭제하고 tool별 `*_input_schema()`와
  `validate_present_<x>()`로 교체했다. `event_adapter.py`의 present 전용 디코딩 분기도 삭제해
  다른 Tool과 같은 일반 경로를 탄다.
  `PresentError`/`_fail`, `check_accessible`/`read_chart`(Result Store 교차 검증)는 그대로
  재사용했다.
  여러 결과를 한 화면에 묶는 `Card`/`SimulationSummary` 자식 기능은 뺐다 — 프론트에 여러 tool
  호출을 하나로 묶는 기존 메커니즘이 없어 범위가 커지므로, 여러 `present_*` 호출은
  `execute_sql` 여러 번 호출처럼 순차적으로 나열되고 연결은 모델이 텍스트로 설명한다.
  `agent_sdk_present/CLAUDE.md`와 `.claude/skills/{simulation,sql-analysis}/SKILL.md`를 이
  계약에 맞춰 다시 썼다.
- 검증: `pytest -q` 418 passed, 6 deselected(`test_present.py`, `test_prompt_consistency_present.py`,
  `test_result_ui_mode.py` 전면 재작성 포함). 실제 provider(GLM-5.3-flash)로 이전에 반복
  실패하던 시나리오("지표 2개, 차트 2개 보여줘")를 재현해 `present_chart` 2회 호출이 모두
  `is_error` 없이 `{}` 성공으로 끝나는 것을 SSE로 직접 확인했다.
- 미수행: `present_*` 운영 기본값 결정(위 항목과 동일), Card 상당의 시각적 grouping이
  필요한지 여부는 실사용 피드백을 보고 재검토.

### 2026-09-22 — Result Store 표 검색·정렬·pagination

- table API에 `search`·`sort_column`·`sort_direction`을 추가하고, 저장된 최대 1,000건을
  먼저 검색·정렬한 뒤 요청된 page만 반환하도록 변경했다. 응답은 전체 `row_count`와
  검색 후 `filtered_row_count`를 구분한다.
- 검증: `python -m pytest -q` 430 passed, 6 deselected.

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

### 2026-09-21 — 구조화 지식 변경 요청·승인

- 구조화 YAML 6종의 변경 요청 워크플로를 구현했다. 초안·이력은 SQLite, 승인 시 정규화 YAML을
  원자적으로 쓰고 store를 즉시 reload하며 실패하면 파일을 복구한다. 기준 YAML 해시가 바뀌면
  409로 막고, 정합성은 이번 변경이 새로 만든 문제만 게이트한다.
- 정합성 규칙을 `tests`에서 `services/knowledge/integrity.py`로 옮겨 승인 게이트와 공유했다.
  `KnowledgeStore`는 항목별 출처 경로를 기억해 파일명과 키가 다른 파일도 제자리에서 갱신한다.
- 인증 전환용 `Principal`과 권한 단위 의존성을 추가했다(스텁, 보안 경계 아님).
- 결정: 초안·이력은 SQLite/최종은 YAML(단일 기준 유지), 자기 승인 기본 차단, 삭제 없이
  `active:false` 요청으로 비활성화, 승인 즉시 reload는 단일 워커 전제.

### 2026-09-21 — 실행·운영 기준 정리

- 실행 환경을 Conda에서 Python 3.11 `.venv`로 통일하고 Backend 포트를 8100으로
  정리했다.
- `services` 공개 경계에 구조화 logging을 적용하고 입력·SQL·결과·경로·scope가
  로그에 노출되지 않도록 했다.
- 상세 날짜형 계획을 이 문서로 통합하고 Backend workspace 독립 계획 체계로
  전환했다.
- SMT2020 원본·생성 DB·변환 도구를 개발용 mock 회귀 자산으로 한정했다. 자산이
  없는 환경에서는 관련 테스트만 skip하며, 폐쇄망은 prod/production/별도 운영 지식을
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
- 2026-09-23 기준 전체 개발 검증: **377 passed, 6 deselected**. 마커 제외
  프로필(`not bundled_knowledge and not mock_service and not e2e`)은
  **312 passed, 71 deselected**다. 이 검증은 실제 사내 provider 연결을 포함하지 않는다.
- 재측정한 검증은 Starlette TestClient의 upstream deprecation warning 1건만 남는다.
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
