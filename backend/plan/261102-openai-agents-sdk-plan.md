# OpenAI Agents SDK 실행부 추가 계획

Claude Agent SDK로 구현한 Agent 실행부 옆에 OpenAI Agents SDK 실행부를 하나 더 만든다. 두 실행부를 같은 평가 세트로
비교한 뒤 기본값 전환을 결정한다. Frontend와 공개 API·`AgentEvent` 계약은 바꾸지 않는다.

## 배경과 목표

- 현재 GPT(gpt-5.4)는 Claude Agent SDK → Claude CLI(Node) → `/anthropic` 변환 프록시(`services/llm/azure_openai_proxy.py`)
  → 사내 게이트웨이 경로로 호출한다. 형식 변환 때문에 생긴 문제(지원하지 않는 파라미터 제거, CLI User-Agent 차단 우회,
  `unrecognized_model` 경고)와 폐쇄망 반입 부담(Node 런타임·CLI)이 있다.
- 목표: OpenAI Agents SDK(`openai-agents`)로 게이트웨이를 직접 호출하는 실행부를 추가하고, 품질·속도가 같거나 나으면
  기본 실행부로 전환한다.
- 비목표: Frontend 변경, 모델 변경, 대화·결과의 영속 저장(별도 Todo), Claude 실행부와 변환 프록시 삭제(전환 결정 후 별도 작업).

## 범위

| 구분 | 내용 |
| --- | --- |
| 바뀌는 곳 | `agent/` 실행부(새 모듈 추가, `run_agent` 분기), Tool 등록 계층의 공통화, 실행부 테스트, 평가 스크립트, `core/config.py`, `.env.example`, `requirements.txt`, 문서 |
| 그대로 두는 곳 | `tools/`·`services/`(SQL 가드·Result Store·지식·시뮬레이션), `api/` 라우트와 `api/schemas.py`, 지식 YAML, 런타임 지침 내용(`agent_sdk/CLAUDE.md`·Skills), Frontend 전체 |

## 설계

### 1. 실행부 선택

- 새 환경변수 `AGENT_RUNTIME=claude|openai`(기본 `claude`). `core/config.py`에서 읽고 `.env.example`에 비밀값 없이 추가한다.
- `agent/agent.py`의 `run_agent(message, conversation_id, fork_from_turn_id, access_scope)` 시그니처와 반환(`AsyncIterator[AgentEvent]`)은
  그대로 두고, 내부에서 실행부를 고른다. 라우트·평가 스크립트는 `run_agent`만 호출한다.
- 새 모듈(가칭): `agent/openai_runtime.py`(실행), `agent/openai_event_adapter.py`(이벤트 변환), `agent/openai_session_store.py`(대화 기록·분기).
- `AGENT_RUNTIME=openai`일 때 필요한 설정: 게이트웨이 endpoint·key·API version·deployment(기존 `AZURE_OPENAI_*` 재사용).
  설정이 비면 시작 시 명확한 설정 오류를 낸다(기존 `require_production_env`와 같은 방식).

### 2. Tool 등록 공통화

- 현재 `agent/sdk_tools.py`는 Tool 설명·입력 schema를 Claude `@tool` 데코레이터 안에 둔다. 설명을 두 곳에 복제하지 않도록 먼저
  실행부 중립 Tool 명세(`ToolSpec`: name, description, input schema, handler, 화면 노출 여부)를 한 목록으로 뽑는다.
  - Claude 실행부: `ToolSpec` → `@tool`/`create_sdk_mcp_server`(동작 변화 없음).
  - OpenAI 실행부: `ToolSpec` → `FunctionTool(name, description, params_json_schema, on_invoke_tool)`.
- `access_scope`는 지금처럼 Tool 생성 시 클로저로 묶고 모델 입력 schema에는 넣지 않는다.
- 엄격 schema 모드: OpenAI strict 모드는 선택 필드·자유 객체를 허용하지 않는다. 선택 필드(`present_chart.bar_mode`,
  `aggregate_result.labels`, `list_tables.keyword` 등)나 자유 객체(`run_simulation.params`)가 대부분 Tool에 있으므로 모든 Tool을
  `strict_json_schema=False`로 등록하고, 서버 쪽 검증(present·aggregate 서비스)을 그대로 쓴다(2단계 구현).
- `tool_names()`·`TOOL_NAMES`와 Tool 목록 API(`/api/...` UI discovery)는 공통 명세에서 만든다. 공개 이름은 짧은 이름
  (`execute_sql` 등) 그대로다.

### 3. 지침과 Skill

- OpenAI SDK에는 `CLAUDE.md`·`.claude/skills` 자동 로딩이 없다. `instructions`를 `SYSTEM_PROMPT` + `agent_sdk/CLAUDE.md` 본문으로
  조합한다(파일 내용 변경 없음, 로딩 실패 시 시작 오류).
- Skill은 내부 Tool `load_skill(name)`로 제공한다. Skill 이름·한 줄 설명 목록은 instructions에 넣고, 호출하면 해당 `SKILL.md`
  본문(frontmatter 제외)을 돌려준다. 지금의 "필요할 때 Skill을 불러 절차를 읽는" 계층 구조를 유지한다.
- `load_skill`과 `suggest_follow_ups`는 화면 이벤트로 내보내지 않는다(현재 `Skill`·후속질문 Tool과 같은 규칙).

### 4. 모델 연결

- `AsyncAzureOpenAI`(또는 base_url 지정 `AsyncOpenAI`) 클라이언트 + `OpenAIChatCompletionsModel(deployment)`. 게이트웨이가
  Chat Completions + Tool 호출 + 스트리밍을 지원함은 기존 프록시로 확인했다. Responses API는 게이트웨이 지원 여부를 확인하지
  않았으므로 쓰지 않는다.
- `ModelSettings`: `parallel_tool_calls=False`(현재처럼 Tool을 순서대로 호출해 화면 순서·`도입 → present → 해석` 규칙을 유지),
  `include_usage=True`(스트리밍에서 토큰 사용량을 받으려면 필요, 0단계 확인), 추론 계열이 거부하는 temperature 등은 지정하지 않는다.
- **트레이싱 비활성화 필수**: `set_tracing_disabled(True)`. 기본값은 트레이스를 외부(OpenAI)로 보내므로 폐쇄망·보안 원칙에 어긋난다.
  테스트로 비활성화 상태를 단정한다.
- `max_turns`: SDK 기본값(10)은 Tool 9회 + 후속질문을 쓰는 현재 응답에 부족하다. 설정값(`AGENT_MAX_TURNS`, 기본 25)으로 둔다.
  초과 시 공개 오류 문구로 `error` 다음 `done`.

### 5. 이벤트 변환(`AgentEvent` 계약 유지)

| OpenAI Agents SDK 스트림 | `AgentEvent` | 비고 |
| --- | --- | --- |
| 텍스트 delta(raw response 이벤트) | `text` | 최종 메시지 item으로 같은 텍스트를 다시 보내지 않는다 |
| `tool_called` run item | `tool_call` + `status`(running) | `tool_call_id`=모델의 call id, args는 파싱된 dict |
| `tool_output` run item | `tool_result` + `status`(completed/error) | `status:error` payload·예외는 지금과 같은 안전한 문구로 |
| reasoning item·추론 요약 | 내보내지 않음 | 내부 추론 비공개 원칙 |
| `load_skill`·`suggest_follow_ups` 호출·결과 | 내보내지 않음 | 후속질문은 마지막 유효 값만 `done.data.suggestions` |
| 정상 종료 | `done`(`data.turn_id`, `suggestions`) | 성공한 턴에만 `turn_id` 발급 |
| 예외·취소·max_turns 초과·타임아웃 | `error` 다음 `done` | 내부 예외·provider 정보 비공개 |

- 같은 호출은 `tool_call`과 `tool_result`에서 같은 `tool_call_id`를 쓴다.
- 이벤트 순서(텍스트 → Tool → 텍스트)는 현재 Claude 어댑터와 같아야 한다. 같은 가짜 시나리오를 두 어댑터에 넣어 같은
  `AgentEvent` 목록이 나오는지 비교하는 테스트로 확인한다.

### 6. 대화 기록과 분기(편집·재생성)

- 현재: conversation → Claude session_id, turn_id → (session_id, 마지막 entry uuid)로 SDK의 `fork_session`을 쓴다.
- OpenAI 실행부: 턴이 성공하면 그 시점의 전체 입력 기록(`result.to_input_list()`)을 저장한다.
  - conversation_id → 최신 기록, turn_id → 그 턴 직후 기록 스냅샷.
  - 평범한 다음 턴: conversation의 최신 기록 + 새 사용자 메시지로 실행한다.
  - `fork_from_turn_id`: 해당 스냅샷 + 새 메시지로 실행해 새 갈래를 만든다(원본 기록은 바꾸지 않음).
  - 빈 문자열은 처음부터, 알 수 없는 turn_id는 지금과 같은 경고 `error` 후 새 대화.
- 저장은 현재와 같은 프로세스 메모리(재시작 시 소멸)로 시작한다. 영속 저장은 기존 Todo(인증 principal·영속 대화 설계)에서 다룬다.
  스냅샷이 대화마다 쌓이므로 대화당 보관 턴 수 상한을 둔다(초과분은 오래된 turn_id부터 제거, 그 turn_id로 분기하면 새 대화 경고).
- Tool 결과는 이미 bounded preview라 기록 크기가 크지 않지만, 기록 전체를 매 턴 재전송하므로 긴 대화의 토큰 증가를 평가 때 기록한다.

### 7. 타임아웃·오류·비용

- `LLM_RESPONSE_TIMEOUT_SECONDS`(기본 30초) 동안 스트림 이벤트가 없으면 실행을 취소하고 기존 공개 문구로 `error` → `done`.
- 재시도(7단계 반영): 게이트웨이는 요청 제한 시 429와 `Retry-After: 60`을 준다. OpenAI 클라이언트 재시도(`max_retries=0`)는 끄고
  runner 재시도 정책(`RetryWait`)이 408·409·429·5xx·네트워크 오류를 1·2·4·8·16·32초 지수 backoff로 다시 보낸다. 재시도를 기다리는
  동안은 응답 지연으로 세지 않고, 대기가 끝난 뒤부터 한도를 센다(Claude 실행부는 SDK 재시도 진행 이벤트로 같은 효과를 얻는다).
- 비용: SDK가 USD 비용을 주지 않으므로 평가 스크립트는 토큰 사용량(입력·출력)을 기록하고, 단가 설정이 있을 때만 USD로 환산한다.
  지금 0.48 USD처럼 Claude 요금표로 잘못 추정된 값을 쓰지 않는다.

## 단계와 완료 조건

| 단계 | 작업 | 완료 조건 |
| --- | --- | --- |
| 0. 사전 확인 | `openai-agents`(작성 시점 안정 버전 고정)와 의존성을 오프라인 wheel로 설치 가능한지, 트레이싱 비활성화 시 외부 요청이 없는지, 게이트웨이 Chat Completions 스트리밍+Tool 호출이 SDK로 동작하는지 작은 스크립트로 확인 | 확인 결과를 이 문서에 기록. 막히면 중단하고 결정 요청 |
| 1. Tool 명세 공통화 | `ToolSpec` 목록 추출, Claude 실행부는 동작 변화 없음 | 기존 Backend 테스트 전부 통과, 프롬프트 정합성 테스트가 공통 명세를 대상으로 동작 |
| 2. OpenAI 실행부 | 실행·지침 조합·`load_skill`·모델 연결·트레이싱 off·max_turns | 가짜 모델로 텍스트·Tool·후속질문 흐름 단위 테스트 통과 |
| 3. 이벤트 어댑터 | 5절 대응표 구현 | 어댑터 단위 테스트, 두 어댑터 동일 시나리오 비교 테스트 통과 |
| 4. 기록·분기 | 6절 구현 | 다음 턴·편집 분기·재생성·알 수 없는 turn_id·상한 초과 테스트 통과 |
| 5. 오류·타임아웃 | 7절 구현 | 타임아웃·예외·max_turns 초과 시 `error` → `done` 테스트 통과 |
| 6. 앱 검증 | `AGENT_RUNTIME=openai`로 Backend 실행, 브라우저에서 SQL·차트·문서·시뮬레이션·데이터 없음·삭제 요청·질문 편집·재생성·후속질문 클릭 확인 | Frontend 테스트·빌드 변경 없이 통과, 화면 동작이 Claude 실행부와 같음 |
| 7. 비교 평가 | 같은 gpt-5.4로 평가 세트 15문항을 두 실행부에서 각 2회 실행 | 아래 전환 기준 판정과 결과를 History에 기록 |
| 8. 문서 | README·`docs/CLOSED_NETWORK_SETUP.md`(반입 패키지, Node/CLI 불필요 조건)·`AGENTS.md`·`.env.example`·`requirements.txt` | 링크·명령 확인, `git diff --check` |

## 0단계 확인 결과(2026-11-02)

임시 venv(Python 3.11, Windows)와 1회용 확인 스크립트로 확인했다. 스크립트는 저장소에 넣지 않았다.

| 항목 | 결과 |
| --- | --- |
| 패키지 | `openai-agents==0.24.0`(2026-10-15 배포, 순수 Python wheel, Python ≥3.10)으로 고정한다. `requirements.txt` 전체와 함께 설치해도 `pip check` 충돌이 없다. 현재 개발 venv에 없는 패키지는 `openai-agents`, `griffelib` 2개뿐이고 나머지 의존성(`openai<4,>=3`, `httpx2`, `mcp`, `starlette`, `websockets` 등)은 이미 설치된 버전 범위로 충족된다. 폐쇄망은 사내 Nexus로 설치하므로 이 2개 패키지의 Nexus 등록 여부를 반입 전에 확인해야 한다(여기서는 확인 불가). |
| 트레이싱 | `set_tracing_disabled(True)`이면 실행 중 DNS 조회 호스트가 게이트웨이 하나뿐이다. 대조군(기본값, 더미 `OPENAI_API_KEY`)은 `api.openai.com`(트레이스 수집 endpoint)으로 접속을 시도했다(확인 스크립트가 DNS 단계에서 차단). 기본값이 외부 전송이므로 비활성화는 필수이며, 실행부 import 시점에 끄고 테스트로 단정한다. |
| 게이트웨이 호환 | `AsyncAzureOpenAI(azure_endpoint, api_key, api_version)` + `OpenAIChatCompletionsModel(deployment)`가 기존 `AZURE_OPENAI_*` 설정 그대로 동작한다. 스트리밍 텍스트 delta, Tool 호출(call id·인자 dict), `parallel_tool_calls=False`, `strict_json_schema=False` raw schema의 선택 필드 생략 호출 모두 거부 없이 처리됐다. SDK 기본 User-Agent는 차단되지 않았다. |
| 다음 턴 기록 | `result.to_input_list()`(user → function_call → function_call_output → message 4항목)에 새 사용자 메시지를 붙여 실행하면 직전 Tool 결과 값을 이어서 답한다. 6절 스냅샷 분기 방식이 가능하다. |
| 토큰 사용량 | 스트리밍은 `include_usage=True`를 줘야 `usage.input_tokens/output_tokens`가 채워진다(없으면 0). 4절에 반영했다. |
| 이벤트 순서 | `tool_called` → `tool_output` → 텍스트 delta 순서로 나와 5절 대응표대로 변환할 수 있다. Chat Completions 경로라 reasoning item은 나오지 않았다. |

결론: 막힌 항목이 없어 1단계(Tool 명세 공통화)로 진행할 수 있다. 남은 선행 확인은 폐쇄망 Nexus의 2개 패키지 등록 여부다.

## 전환 기준(7단계)

- 최종 답변 정답률·조회 데이터 정답률이 Claude 실행부 이상.
- 응답 시간 p50·p90이 Claude 실행부보다 나쁘지 않음(같은 게이트웨이·같은 날 측정).
- SQL 오류율·쓰기 SQL 시도·출처 표기율·후속질문 제공률 등 규칙 지표가 같거나 나음.
- 질문 편집·재생성 분기가 앱에서 정상 동작.
- 충족하면 기본값을 `openai`로 바꾸고, Claude 실행부·변환 프록시·CLI 의존 제거는 별도 작업으로 Todo에 등록한다.
  충족하지 않으면 원인을 기록하고 `claude`를 기본으로 둔다.

## 위험과 대응

| 위험 | 대응 |
| --- | --- |
| 트레이싱이 외부로 데이터 전송 | 실행부 시작 시 비활성화, 테스트로 단정, 폐쇄망 문서에 명시 |
| 지침이 Claude 실행부 기준으로 다듬어져 있음(Tool 설명 우선 등) | 지침 내용은 바꾸지 않고 시작, 7단계 결과로 차이가 나는 규칙만 조정 |
| strict schema 비활성으로 잘못된 인자 증가 | 서버 쪽 schema·교차 검증과 오류 보정(최대 2회) 규칙 유지, 평가에서 Tool 오류율 비교 |
| 병렬 Tool 호출 시 화면 순서 깨짐 | `parallel_tool_calls=False` |
| 기록 재전송으로 긴 대화 토큰 증가 | 평가에 다중 턴 문항 추가 시 토큰 기록, 필요하면 오래된 Tool 결과 요약을 별도 검토 |
| 패키지 반입 불가 | 0단계에서 확인, 불가하면 계획 중단 |
