# Backend 완료 이력

완료한 업무의 결과, 중요한 결정과 검증 근거를 보존한다. 현재 계약은 [진행 중](InProgress.md), 남은 일은 [할 일과 아이디어](Todo.md)를 따른다.

## 2026-10-23 — SQL 방언 안내(`SQL_DIALECT`)

- "이번 달" 질문마다 첫 SQL이 `TO_CHAR(CURRENT_DATE, 'YYYYMM')`(Oracle 계열)로 실패해 mock SQLite에서
  `no such function`이 났다. Agent가 DB 방언을 몰랐고 카탈로그 규칙의 `NVL`도 Oracle식이다.
- mock·production `sql_service`가 같은 이름의 `SQL_DIALECT`를 공개한다(mock `SQLite`, production은 새 환경변수
  `PRODUCTION_SQL_DIALECT`, 비우면 안내 없음). `agent/sdk_tools.py` `sql_dialect_note()`가 이를 `execute_sql` 설명에
  넣고, SQLite면 NVL→COALESCE·오늘 연월 `strftime('%Y%m', 'now', 'localtime')`(UTC 회피)·YYYYMMDD 문자열은 `substr(컬럼, 1, 6)`을 안내한다.
  mock SQL 실행 오류 메시지에도 방언을 덧붙인다. `.env.example`·`docs/CLOSED_NETWORK_SETUP.md`에 키를 추가했다.
- 첫 안내에 `TO_CHAR→strftime(날짜)` 예시를 넣었더니 YYYYMMDD 문자열 `WORK_DT`에 `strftime`을 써 NULL이 되고
  "월이 비어 있다"는 오판이 나왔다. 저장 형식 확인과 `substr` 안내로 고쳤다.
- 재실행: SQL 오류 없이 `WORK_YM = strftime('%Y%m', 'now')`(0건) → 보유 월 확인(202601~202606) → 확인 질문으로 멈춤.
  `tests/test_sql_dialect.py` 4건 추가, Backend 414 passed.

## 2026-10-23 — 확인 질문 선택지를 확인된 범위로 제한

- 데이터 없는 월을 물었을 때 선택지에 "다른 테이블로 확인"이 나왔지만 계획수량은 해당 테이블에만 있다.
  `agent_sdk/CLAUDE.md`·`sql-analysis` Skill에 "선택지는 조회로 데이터가 있음을 확인한 기간·대상만, 카탈로그에서
  확인하지 않은 다른 테이블·기준은 내지 않는다"를 추가했다.
- 같은 2턴 재실행: 선택지가 "6월 기준" 또는 "1~6월 월별 추이"로만 제시되고 다른 테이블·대체 수치·후속질문 없음.

## 2026-10-23 — 지정 기간에 데이터가 없으면 기준을 바꾸지 않고 확인

- "이번 달 계획 달성률"(10월, 데이터 없음)에 gpt-5.4가 묻지 않고 최근 월(6월)로 바꿔 52.33%를 답했다. 기준을
  밝히긴 했지만 "빠진 조건을 임의로 만들지 않는다" 원칙과 어긋나, 사용자 결정에 따라 멈추고 확인하는 쪽으로 정했다.
- `agent_sdk/CLAUDE.md`에 "지정한 기간·대상·기준에 데이터가 없으면 다른 기준으로 바꿔 답하지 않고, 없다는 사실과
  조회 가능한 범위를 알린 뒤 어느 기준으로 볼지 묻고 멈춘다(후속질문 미호출)"를, `sql-analysis` Skill의 0행 검증
  단계에 같은 절차를 추가했다.
- 같은 질문 재실행: "이번 달 데이터 없음, 보유 범위 202601~202606"을 알리고 기준 선택지(6월, 특정 월, 월별 추이)를
  물은 뒤 멈췄다. 대체 수치·차트·후속질문 버튼은 나오지 않았다.

## 2026-10-23 — 답변 본문의 추가 제안 문장 금지

- 문서 답변 끝에 "원하시면 MTBPM·MTTF·MTTR를 예시로 비교해 드리겠습니다"처럼 후속질문과 겹치는 제안 문장이
  남았다. `agent_sdk/CLAUDE.md` 후속질문 규칙에 "답이 완결된 응답에서는 본문 끝 추가 제안 문장을 쓰지 않고
  `suggest_follow_ups`로만 제안, 모호해 선택이 필요한 확인 질문은 본문에 쓴다"를 넣고 Tool 설명에도 반영했다.
- 같은 질문 재실행: 본문은 요약으로 끝나고 제안 문장 없음, 후속질문 3개는 버튼으로만 표시, 출처 표기 유지.

## 2026-10-23 — 조회 결과 요약 필드명 비노출

- 답변 근거에 "distinct_counts.part = 10, top_groups.dataset…"처럼 SQL 미리보기 요약의 필드명이 노출됐다.
  `agent_sdk/CLAUDE.md` 내부 식별자 규칙에 `row_count`·`distinct_counts`·`top_groups`·`sample_rows`·
  `statistics` 등을 넣고 "전체 12행", "고유 Part 10개"처럼 풀어 쓰게 했으며, `execute_sql` 설명에도 같은 문구를 넣었다.
- 같은 질문 재실행: 요약 필드명·레시피 ID·Tool 이름·`result_id` 노출 없음, Part별 수치 정답 일치.

## 2026-10-23 — 지식 항목 내부 ID 비노출

- gpt-5.4 답변에 레시피 ID(`initial_wip_by_part`)가 노출됐다. `agent_sdk/CLAUDE.md`의 내부 식별자 규칙에
  레시피·KPI·시뮬레이션·시나리오 ID를 포함하고 결과의 `name`(표시 이름)으로 부르게 했으며, `get_recipe`·`get_kpi`
  설명에도 "ID 대신 name" 문구를 넣었다. 테이블·컬럼명과 문서 출처 ID는 근거 표기로 계속 허용한다.
- 같은 질문 재실행: ID 대신 "Part별 초기 WIP 레시피"로 표기, Tool 이름·`result_id` 노출 없음. 미리보기 통계
  필드명(`distinct_counts`·`top_groups`)이 근거 문장에 남는 점은 별도로 관찰됐다.

## 2026-10-23 — 단위가 다른 지표 합산 차트 차단

- gpt-5.4가 Lot 수·수량(piece)을 long 형식 한 결과에 담고 `group_by_column=dataset`, `aggregation=sum`으로
  차트를 그려 두 지표가 한 막대에 합산됐다(예: 1,128 + 113,932).
- `services/results/chart.py` `project_chart`가 지표 이름으로 보이는 범주 컬럼(`metric`·`measure`·
  `indicator`·`kpi`·`지표` 포함)에 값이 둘 이상인데 x·group_by가 아니면 `INVALID_REQUEST`(details: column,
  values)로 거부한다. `present_chart` 검증과 `/api/query-results/{id}/chart`가 같은 경로라 함께 막히며 오류
  코드는 기존 계약 안에서 쓴다. 지표가 아닌 범주(예: 영업배치)의 합산은 그대로 허용한다.
- `present_chart` 설명·`agent_sdk/CLAUDE.md`·`sql-analysis` Skill에 합산 동작과 "단위가 다른 지표는 지표별로
  따로" 규칙을 보강했다. 재실행에서는 Agent가 Lot 수·수량을 wide 표로만 제시해 서버 거부 경로는 타지 않았다.

## 2026-10-23 — 카탈로그 키워드 검색 보강

- gpt-5.4가 `list_tables`를 "계획 실적"·"plan actual"처럼 띄어 쓴 키워드로만 검색해 0건을 받고 답을
  포기했다(키워드 전체 문자열 부분일치라 "계획실적" 태그·"계획·실적" 설명과 맞지 않음).
- `services/knowledge/catalog.py` `_contains`가 키워드를 공백·가운뎃점·쉼표·슬래시로 나눈 단어 중 하나라도
  맞으면 일치로 보고, 공백·가운뎃점을 뺀 형태로도 비교한다(`list_tables`·`list_kpis`·`list_recipes` 공통).
  필터 검색 결과가 비면 catalog payload에 `message`로 "필터 없이 다시 호출" 안내를 담고, `list_tables`
  설명에 0건이면 전체 목록을 보고 판단하라고 적었다. Frontend는 `data`만 읽어 영향이 없다.
- 같은 질문 재실행: Tool 4회로 실적 0 계획 11건(제품·영업배치·공정·월 단위, 계획 36,903)을 답했다.
  일 단위 원본 행 기준(17건, 46,204)과는 집계 단위가 다르며, 답변이 그 기준을 밝혔다.

## 2026-10-23 — `query_rules` 기본 제외 조건 적용 지침

- gpt-5.4 SQL에서 미수립계획 제외(`PLAN_OPT_CD = 'X'`)가 빠졌다. 카탈로그 규칙이 "명시 요청 시에만
  포함"이라는 포함 조건 형태라 제외 필터로 옮기지 못한 것으로 보고, `agent_sdk/CLAUDE.md`·`sql-analysis`
  Skill에 "기본 조건은 요청이 없으면 WHERE 필터로 반드시 적용하고, '요청 시에만 포함'은 해당 코드값
  행 제외(NULL 행은 유지)"를 추가했다. 덧붙이지 말 필터(필수 포함 컬럼)와 반드시 넣을 필터를 구분한다.
- Skill이 특정 컬럼명을 복제하지 않도록 기존 long 형식 예시도 `<차원>`·`<지표 A>` 같은 일반 표기로 바꿨다.
- 재실행 SQL에 `(PLAN_OPT_CD IS NULL OR PLAN_OPT_CD <> 'X')`가 들어가고 `SALES_BATCH_CD`는 그룹 컬럼으로만
  쓰였다. 답변 결론에서 최저 달성률 지역을 잘못 적는 모델 오류가 별도로 관찰됐다.

## 2026-10-19 — 내부 식별자 비노출·"필수 포함" 규칙 해석 지침

- gpt-5.4가 답변 본문에 `result_id`를 쓰고, `query_rules`의 "SALES_BATCH_CD를 필수로 포함한다"를
  `SALES_BATCH_CD IS NOT NULL` 필터로 해석했다. 지식 YAML은 바꾸지 않고(승인 시 verified로 바뀌는
  부작용) 해석 원칙을 `agent_sdk/CLAUDE.md`·`sql-analysis` Skill에, `result_id` 비노출을
  `execute_sql` 설명에 추가했다. "필수 포함"은 결과 컬럼에 넣으라는 뜻이며 제외 필터로 바꾸거나
  질문·규칙에 없는 필터를 덧붙이지 않는다. 답변에는 `result_id`·Tool 이름을 쓰지 않는다.
- 같은 질문 재실행: `result_id`·Tool 이름 노출 없음, `SALES_BATCH_CD`는 상세 표 컬럼으로 포함되고
  NOT NULL 필터 없음, 등급별 수치 정답 일치. Tool 호출은 13회로 늘었다(이전 7회, 모델 편차).

## 2026-10-19 — 여러 지표 비교 차트 묶기 지침

- gpt-5.4가 계획·실적 비교 요청에 지표별 차트 2개를 그리고 조회 월(고정값)을 계열로 쓴 문제가
  있었다. `present_chart` 설명의 "지표별로 따로 보여줄 때" 예시를 지우고, 비교 지표는 지표 이름·값의
  long 형식으로 조회해 `group_by_column`=지표 이름으로 한 번 호출하며 고정값 컬럼은 계열로 쓰지 않고
  단위가 다른 지표만 나눈다는 규칙을 Tool 설명·`agent_sdk/CLAUDE.md`·`sql-analysis` Skill(UNION ALL
  예시)에 추가했다. 프롬프트 정합성 테스트에 단정을 추가했다.
- 같은 질문을 gpt-5.4로 다시 실행해 막대 차트 1개(계열 2개: 계획수량·실적수량), Tool 9회로 줄어든
  것을 확인했다(이전 차트 2개, Tool 11회, 오류 1회).

## 2026-10-19 — Azure OpenAI 호환 게이트웨이 연결(`LLM_PROVIDER=azure_openai`)

- GPT 계열만 제공하는 Azure OpenAI 호환 게이트웨이를 쓰기 위해 `services/llm/azure_openai_proxy.py`에
  Anthropic Messages ↔ chat completions 변환(텍스트·이미지·tool_use/tool_result·tool_choice·
  스트리밍 SSE 재구성·count_tokens 근사)을 구현하고 `/anthropic` 경로가 이 provider일 때만 쓰게 했다.
  `local`은 기존대로 폐쇄망 구현 반입 전 501을 유지한다.
- CLI는 서버 프로세스마다 생성한 `LOCAL_PROXY_TOKEN`으로만 프록시를 호출한다. thinking·
  cache_control·temperature·stop은 전달하지 않는다(reasoning 계열 거부 방지). Claude 모델명
  요청은 `AZURE_OPENAI_DEPLOYMENT`로 바꾼다.
- 실제 게이트웨이 확인: gpt-4.1·gpt-5-mini·gpt-5.4 모두 Tool 호출·스트리밍 지원. `/api/chat`
  관통 시 gpt-4.1은 테이블 검색 0건에서 답을 포기했고, gpt-5.4는 describe_table→SQL→규칙
  적용→후속질문까지 정답(6월 계획 139,953)을 냈다.
- `tests/test_azure_openai_proxy.py` 11건(변환·인증·비스트리밍/스트리밍 관통·오류 비노출) 추가.

## 2026-10-19 — Agent 정량 평가 도구

- `evals/agent_eval_set.yaml`(13문항: SQL 8·문서 2·시뮬레이션 1·데이터 없음 1·삭제
  요청 1)과 `scripts/evaluate_agent.py`를 추가했다. 정답은 질문마다 `truth_sql`로 합성
  mock DB에서 다시 계산한다.
- 운영 지표: 최종 답변 정답률(SQL은 조회 데이터 정답률과 분리), 응답 완료율, 응답 시간
  p50/p90·첫 응답, SQL 전 `describe_table` 규칙 준수율, SQL 오류율, 쓰기 SQL 시도 수,
  문서 출처 표기율, 후속질문 제공률, 평균 Tool 호출, 질문당 비용(SDK `ResultMessage`).
  정적 지표: 구조화 지식 verified 비율, SQL 가드 차단율(공격 쿼리 12개).
- 질문별 실패는 기록하고 계속하며, 크레딧·인증·CLI 연결 오류는 남은 질문을 미실행으로
  남기고 멈춘다. 결과는 `artifacts/evals/`(Git 제외)에 JSON·Markdown으로 저장한다.
- 첫 실행은 SQL 6문항 뒤 API 크레딧 부족으로 중단됐고, 충전 후 13문항 전체 기준선을
  측정했다: 정답률·완료율·규칙 준수율·출처 표기율·후속질문 제공률 100%, SQL 오류율 0%,
  쓰기 SQL 시도 0건, 응답 p50 31.1초·p90 39.8초·첫 응답 p50 18.7초, 평균 Tool 4.8회,
  질문당 0.25 USD(전체 3.26 USD). 정적 지표는 verified 56.7%(30개 중 17개), 가드 차단
  100%. 13문항 전부 통과해 변별력이 없으므로 문항 확대가 필요하다.
  `tests/test_agent_eval.py` 13건 통과.

## 2026-10-15 — Windows 실패 테스트 4건 수정

- 지식 YAML 원자 쓰기를 바이트 쓰기로 바꿔, Windows에서 승인 실패 후 복구한 파일에
  `\r\r\n`이 생기던 문제를 고쳤다. 새로 쓰는 YAML도 운영체제와 무관하게 LF로 남는다.
- `KnowledgeStore.source_paths`를 `as_posix()`로 기록해 Windows에서도
  `catalog/tables/wip.yaml` 형식을 유지한다.
- mock DB 반복 생성 테스트가 `sqlite3` 연결을 닫지 않아 Windows에서 파일 교체가
  거부되던 문제를 `contextlib.closing`으로 고쳤다. 생성기는 변경하지 않았다.
- starlette 1.8.0 CORS 미들웨어가 `Vary: Origin`을 덧붙여, 결과 API 테스트가
  `Vary`에 `Cookie`가 포함됐는지만 확인하도록 완화했다.
- Windows에서 Backend 381 passed(2회 연속).

## 2026-10-15 — 후속질문 동적 생성

- Agent가 최종 답변 직전에 내부 Tool `suggest_follow_ups(questions)`로 후속질문
  2~4개를 등록하고, Backend가 검증을 통과한 마지막 값만 성공한 `done.data.suggestions`에
  싣는다. 별도 LLM 호출을 추가하지 않아 응답 지연과 비용이 늘지 않는다.
- 검증은 `tools/suggestion_tool.py`의 `normalize_suggestions` 한 곳에서 한다(공백·중복
  제거, 각 1~120자, 한글 포함, 2~4개). 실패하면 보정하지 않고 생략하며 응답은 성공으로 끝난다.
- 이 Tool은 Tool trace에 노출하지 않는다. 런타임 `agent_sdk/CLAUDE.md`에 호출 시점과
  수치·결론을 질문에 미리 적지 않는 규칙을 추가했다.
- 실제 응답에서 답변이 이미 설명한 내용("WIP와 Order는 어떻게 구분되나요?")이
  후속질문으로 나와, 이미 다룬 내용과 후속질문끼리의 반복을 금지하는 규칙을 지침과
  Tool 설명에 추가했다.
- `tests/test_suggestions.py` 추가. 실제 Agent 응답에서 후속질문 4개가 표시되고 클릭 시
  전송되는 것을 확인했다. Windows 환경 차이로 실패하는 기존 4건을 제외하고 통과.

## 2026-10-13 — Agent SDK env 전달 오류 수정

- `LLM_PROVIDER=anthropic`에서 `ClaudeAgentOptions.env`에 `None`을 넘겨
  `claude-agent-sdk` 0.2.152가 모든 채팅을 `CLIConnectionError`로 실패시켰다.
  빈 dict를 그대로 넘기도록 고쳤다.

## 2026-09-30 — 계획·가이드 문서 역할 정리

- 할 일과 아이디어를 `Todo.md`, 현재 상태·계약을 `InProgress.md`, 완료 기록을
  이 파일로 분리했다. 폐쇄망·도메인 지식 docs는 반복해서 사용하는 업무 가이드로 둔다.
- 계획·docs의 `AGENTS.md`와 `CLAUDE.md`, README 진입 링크를 새 역할에 맞췄다.

## 완료 기록

### 2026-10-01 — `present_chart` 누적 막대 모드

- `present_chart`에 선택 입력 `bar_mode: grouped|stacked`를 추가했다. 생략 시
  grouped를 유지하며 stacked는 `chart_type=bar`와 `group_by_column`을 요구한다.
- 같은 단위의 합산 가능한 그룹 구성에만 stacked를 권하도록 Tool 설명과 Agent
  지침을 갱신했다. 집계 chart API 응답 계약은 바꾸지 않았다.
- Backend 전체 검증: 365 passed, 6 deselected.

### 2026-09-28 — LLM 응답 지연 timeout 안내

- Agent SDK가 다음 LLM 이벤트를 30초 동안 내지 않으면 호출을 취소하고, SSE
  `error` 뒤 `done`으로 종료한다. 공개 오류 문구는 "LLM API 서버 응답이 지연되고
  있습니다. 잠시 후에 다시 시도해 주세요."이며 내부 예외·provider 정보는 노출하지
  않는다. `LLM_RESPONSE_TIMEOUT_SECONDS` 환경변수(기본 30초)로 조정할 수 있다.

### 2026-09-28 — P&T Factory Planning Agent 역할 명시

- 시스템 프롬프트의 역할을 반도체 후공정 P&T(Package & Test) Factory Planning의
  생산계획 분석으로 구체화했다. 제품 수요·주문, 설비·인력·자재의 가용 용량과 공정
  제약을 고려해 실현 가능한 계획을 분석한다는 범위를 명시했다.

### 2026-09-28 — RAG 최종 응답 인용 필수화

- 런타임 Agent 지침에서 `search_documents`를 근거로 한 최종 응답은 문서 제목과
  `source` 또는 검색 결과 URL을 반드시 포함하도록 했다. URL이 있으면 우선 표기하고,
  version도 제공될 때 밝힌다. 출처·URL 모두 없는 결과는 답변 근거로 쓰지 않으며
  임의 인용을 만들지 않는다.

### 2026-09-28 — production SQL API 행 상한 전달

- SQL guard에서 자동 `LIMIT MAX_ROWS + 1` 추가를 제거했다. Production SQL service는
  guard 검증 후 조회 API에 SQL과 `rowLimit=MAX_ROWS`를 전달하며, API 클라이언트
  요청 계약과 폐쇄망 이식 가이드에 이를 명시했다.

### 2026-09-28 — backend 테스트 중복 제거와 파일 통합

- 같은 계층에서 같은 계약을 단정하던 테스트 15개를 삭제했다(동일 본문의 prompt 검사,
  `isinstance(dict)`만 보던 Tool wrapper 검사, 다른 테스트가 이미 덮는 session_store·
  present 등록·mock service 검사). 계층이 다른 store·service·tool·API 테스트는 유지했다.
- 작은 파일을 책임별로 합쳤다: `test_workbench_contract` → `test_api`(case 이름은
  frontend workbench fixture와 대응 유지), `test_session_store` → `test_agent`,
  `test_aggregation_guidance`·`test_knowledge_diagnostics` → `test_bundled_knowledge`,
  e2e 2개 → `test_e2e`, `test_knowledge_search_service` → `test_document_management`.
  `test_real_services`는 내용에 맞게 `test_production_services`로 바꾸고 mock/production
  시그니처 일치 테스트를 옮겼다. 테스트 파일 25개 → 20개, 제품 코드 변경 없음.

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
