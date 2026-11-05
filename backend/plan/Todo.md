# Backend 할 일과 아이디어

새 작업과 떠오른 아이디어를 이곳에 기록한다. 착수한 작업의 결정·진행 상황은 [진행 중](InProgress.md), 완료 결과는 [완료 이력](History.md)으로 옮긴다. 각 workspace의 범위와 현재 계약은 진행 중 문서를 따른다.

## 해야 할 일


### P2

- [ ] Agent 평가 세트(`evals/agent_eval_set.yaml`)를 확대한다. 현재 15문항(기준 없는 질문의 `clarify` 1문항 포함)은 대부분 통과해
  변별력이 없다. 다중 조건·기간 비교·조인·모호한 기준·후속 턴(대화 맥락) 문항을 추가하고,
  같은 문항을 반복 실행해 정답률 편차를 본다.

- [ ] Claude 실행부가 비교 답변의 값 나열 규칙을 OpenAI 실행부보다 덜 지킨다(swap 사이트 비교 3/3, 2026-11-03). Claude 실행부 제거
  결정과 함께 정한다.
- [ ] 실제 업무 데이터로 생산 부진 원인 scenario와 KPI·join·집계 정의를 현업
  검토하고 verified 상태를 갱신한다.
- [ ] 서버 처리 시간 공개 필요성, 측정 의미와 비용을 검토한다. 클라이언트 관측
  시간과 혼동되는 값은 추가하지 않는다.
- [ ] Result Store 저장 backend 교체 필요성을 검토한다. 기준별 후속 재집계는 `aggregate_result`(2026-11-02)로
  지원하며, 필터·조인처럼 더 넓은 후속 계산이 필요한지는 사용 사례를 보고 정한다.

### P3

- [ ] 질문당 토큰을 더 줄인다(2026-11-05 측정, 질문당 약 11만). 추가 축소는 품질 확인 뒤. 규칙은 오답을 막으려고 넣은 것이라 한도가 풀린 뒤 관련 문항으로 품질을 확인하며 줄인다.
  캐시 토큰이 월간 한도에 그대로 계산되는지 게이트웨이 담당자에게 확인한다.
- [ ] 한도가 풀리면 병렬 호출을 SQL 질문 1~2개로 확인한다. 모델 호출 수(7번에서 줄었는지), 표시 순서, 후속질문 품질을 본다. 효과가 없거나 품질이 나빠지면 되돌린다.
- [ ] 한도가 풀리면 Tool 설명 축소 뒤 규칙 준수를 대표 질문 2~3개로 확인한다(값 나열, 한국어 별칭, 데이터 없는 기간 응답, 후속질문). 나빠진 규칙만 되돌린다.
- [ ] 한도가 풀리면 미리보기 축소 뒤 동률 안내("part_1~part_6 6개")와 swap 쌍 서술("SITE_B→SITE_A 828.4")을 각 1~2회만 확인한다.
- [ ] Claude 실행부가 "PKT swap 전체 결과에서 사이트별 계획수량과 목표수량"을 시뮬레이션 대신 `FP_TARGET` SQL(PNT 사이트·TARGET_QTY)로
  답했다(1회, 2026-11-04). OpenAI 실행부는 4/4 `run_simulation`→`aggregate_result`. Claude 실행부를 계속 대체용으로 둘지 정할 때 함께 본다.
- [ ] Claude 실행부는 `monthly_token_cap`을 구분하지 못한다. 프록시가 429를 그대로 넘겨 CLI가 재시도한 뒤 일반 실패 문구를 보여 준다.
  Claude 실행부를 계속 대체용으로 둘지 정할 때 프록시 응답 변환과 함께 본다(2026-11-04, 한도 소진 중이라 동작 확인 전).
- [ ] mock 카탈로그 `orders`·`wip`의 `hotlot` 컬럼에 코드값(`yes`·`no`)과 뜻을 변경 요청 경로로 등록한다. 지금은 지침이 `SELECT DISTINCT`
  확인을 요구해 보완하지만, `codes`가 있으면 확인 조회 없이 바로 바른 조건을 쓴다(2026-11-04 Hot lot 오답).

- [ ] Claude 실행부를 제거할지 정하고, 제거하면 `agent/claude_runtime.py`·`agent/event_adapter.py`·`agent/sdk_tools.py`·`agent/session_store.py`,
  `/anthropic` 프록시(`api/routes_anthropic_proxy.py`·`services/llm/azure_openai_proxy.py`), `LLM_PROVIDER`·`AGENT_MODEL`·
  `CLAUDE_CLI_PATH`·provider 키 설정, `requirements-claude.txt`와 Node.js·CLI 반입 안내를 함께 정리한다. 기본 실행부는 2026-11-03부터
  `openai`이며, 그전에 폐쇄망 Nexus에 `openai-agents==0.24.0`·`griffelib` 등록과 실제 게이트웨이 동작을 확인한다.
- [ ] 테스트 설치(`requirements-dev.txt`)는 Claude 실행부 테스트 때문에 `claude-agent-sdk`를 포함한다. 폐쇄망 Nexus에 이 패키지가 없으면
  Claude 전용 테스트(`test_agent.py`·`test_event_adapter.py`·`test_suggestions.py` 등, `agent.claude_runtime`·`agent.sdk_tools`를 import 하는
  파일)를 패키지가 없을 때 건너뛰게 나누고 dev 요구사항에서 뺀다. `test_api.py`·`test_tool_specs.py`처럼 공통 계약을 같이 검증하는 파일은
  Claude 부분만 분리해야 한다.
- [ ] OpenAI 실행부의 대화 기록·분기(`agent/openai_session_store.py`)는 프로세스 메모리라 재시작·다중 워커에서 이어지지 않는다.
  아래 영속 대화·분기 저장 설계에 OpenAI 실행부 기록(`to_input_list()` 스냅샷) 저장 방식을 포함한다.
- [ ] PoC 해싱 임베딩 검색(2026-10-24)을 의미 검색이 되는 임베딩으로 바꾼다. 사내 임베딩 모델·반입 가능
  런타임(예: ONNX)을 정하고 `services/knowledge/embedding.py`의 `get_embedder()`를 교체한다. 문서가 수천 건을
  넘으면 SQLite 전수 비교 대신 vector DB(Milvus 등) 색인을 검토한다.
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
- [ ] 인증 principal, 영속 대화·분기 저장과 모델 선택 계약(표시 이름 조회는 `GET /api/model-info`로 완료)을 별도
  계획으로 설계한다. 착수 전 실제 인증 principal과 폐쇄망에 반입 가능한 저장소를
  정하고, 소유권·재시작 후 fork·보존 기간·24시간 Result Store TTL이 지난 결과 참조의
  표시 정책을 함께 결정한다. 현재 임시 principal을 보안 경계로 사용하지 않는다.

## 아이디어

- 아직 기록된 아이디어 없음. 검토 전 생각은 이곳에 적고, 작업으로 확정되면 위 목록으로 옮긴다.
