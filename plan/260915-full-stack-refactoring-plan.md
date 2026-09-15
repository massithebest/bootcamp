# 전체 시스템 근거 기반 감사 및 리팩토링

**상태: 완료 (선정한 P0/P1 및 소규모 P2 구현·검증 완료). 마지막 갱신: 2026-09-15.**

## 목표와 범위

Frontend와 Backend를 하나의 시스템으로 추적하고 재현 가능한 계약·스트림·오류 결함을 최소 수정한다. 신규 의존성, SDK/protocol 교체, 세션 persistence, 실제 provider 연결, UI 재설계와 미사용 UI 파일 대량 삭제는 범위 밖이다. 기존 Todo의 사용자 미커밋 두 항목을 보존한다.

## Architecture: 변경 전 실행 흐름

| 단계 / 파일·함수 | 입출력 | 상태 소유와 오류·취소 경계 |
| --- | --- | --- |
| frontend/components/chat/message-input.tsx의 ComposerPrimitive | 입력 문자열 → AppendMessage | assistant-ui가 draft·입력·전송/취소 액션 소유 |
| frontend/hooks/use-agent-chat.ts의 handleNew/Edit/Reload → runTurn/runFromPrefix/streamTurn | AppendMessage → ChatMessage[] / sendChatMessage options | React가 메시지·retry·실행 상태, ref가 AbortController·conversation ID 소유 |
| frontend/lib/chat-api.ts의 sendChatMessage / SseParser / parseAgentEvent | ChatRequestBody → fetch/ReadableStream → AgentEvent | credentials include, AbortSignal, transport 오류를 error/done으로 변환 |
| backend/api/routes_chat.py의 chat/event_generator | ChatRequest → StreamingResponse | pp_session_scope 발급/재사용, 모델 JSON을 data 프레임으로 직렬화, 예외 원문 차단 |
| backend/agent/agent.py의 run_agent/_resolve_resume/_build_options | message/conversation/fork/scope → SDK query → AgentEvent | session_store가 conversation→SDK session 및 turn→transcript anchor 소유 |
| backend/agent/sdk_tools.py의 build_planning_mcp_server와 wrapper | 모델 args → 업무 dict → MCP text JSON | SDK 종속 계층, scope는 closure에만 주입 |
| backend/tools/{sql,simulation,knowledge,result,visualization,rag}_tool.py | Python 업무 인자 → dict | tool은 service 진입점, result tool은 저장 결과 접근 검사 |
| backend/services의 mock/real, sql_guard, result_store, visualization_service | SQL/조회 명세 → DB/parquet/검증 명세 | mock SQL read-only 연결, 100행 inline, 최대 500행 저장, Result Store와 chart validation 분리 |
| backend/agent/event_adapter.py의 convert | SDK message/block → 공개 AgentEvent[] | tool ID 매핑·transcript UUID는 내부; ThinkingBlock 및 내장 tool 제외 |
| frontend/hooks/use-agent-chat.ts의 applyEvent → lib/chat-runtime.ts의 convertMessage | AgentEvent → 순서 있는 parts/statuses → ThreadMessageLike | 원본 메시지는 React 소유, runtime은 변환 결과를 UI에 공급 |
| frontend/components/chat/thread-messages.tsx 및 tool-results | runtime parts/metadata → Markdown·진행·도구·차트 | 공식 Parts/Error/ActionBar, 차트 marker만 GET 조회; UI 집계 없음 |

경로의 frontend 파일은 모두 `frontend/src/` 기준이다. history를 request로 보내지 않는 것은 Backend SDK session resume 구조와 일치한다.

## Findings 및 구현 결정

| ID | 우선순위 | 근거 위치 | 문제 | 사용자/운영 영향 | 제안 | 구현 여부 |
| --- | --- | --- | --- | --- | --- | --- |
| F01 | P1 | chat-api.ts parseAgentEvent/sendChatMessage | type만 확인한 cast, malformed 무시, done 없는 EOF를 성공 처리, done 이후 전달 | 손상/부분 응답을 정상 완료로 오인 | envelope 검증, terminal 단일화, premature EOF error | 구현 완료 |
| F02 | P1 | use-agent-chat.ts runTurn/handleRetry/streamTurn | retry가 user를 추가; render state 기반 중복 실행 방지; 오래된 callback 가능 | 중복 질문·취소 후 상태 오염 | 단일 실행 경로·retry snapshot·controller 소유권 검사 | 구현 완료 |
| F03 | P0 | event_adapter.py _convert_user | SDK is_error content를 그대로 공개 data로 전달 | 내부 예외/경로 노출 가능 | SDK 실패 원문을 안전한 업무 오류로 정규화 | 구현 완료 |
| F04 | P1 | event_adapter.py _convert_user, sdk_tools.py _ok, chat-runtime.ts / tool-result-card.tsx | 업무 status:error도 completed 진행; runtime/card 오류 판정 불일치 | 실패한 도구를 성공으로 표시 | 공개 payload 기준 진행 오류, 프론트 공통 오류 판정 | 구현 완료 |
| F05 | P1 | agent.py run_agent finally | 실패·취소 중에도 session/anchor 기록; SDK Result 오류에도 turn_id | 실패한 응답에 성공 anchor 제공 | 정상 SDK 완료에만 anchor 발급·세션 반영 | 구현 완료 |
| F06 | P1 | tools/result_tool.py get_result_summary/get_result_page | TTL 검사 없음, 손상/삭제 파일 예외 전파 | cleanup 전 만료 결과 접근·tool 중단 | scope/TTL 확인 후 안전한 오류 반환 | 구현 완료 |
| F07 | P0 | sql_guard.py _TABLE_REF, mock_sql_service.py execute_sql | 인용한 테이블명을 regex가 놓침 | catalog 외 테이블 조회 가능 | SQLite authorizer로 실제 읽는 테이블 재검사 | 구현 완료 |
| F08 | P1 | simulation-result.tsx, database-result.tsx, knowledge-result.tsx, catalog-result.tsx | 숫자 KPI를 str로 읽음; summary/목록/recipe와 mock RAG 필드 누락 | 실제 tool 결과가 빈 카드/대시로 표시 | 기존 producer payload 그대로 표시하는 작은 renderer 수정 | 구현 완료 |
| F09 | P2 | use-agent-chat.ts applyEvent/status helpers | 상태 소유와 순수 이벤트 변환 결합, 재현 테스트 경계 없음 | lifecycle 수정 시 순서/상태 회귀 위험 | 순수 이벤트 적용 모듈 분리 (상태 소유권 유지) | 구현 완료 |
| F10 | P2 | agent.py _use_fake_runner; tools/sql_tool.py docstring | config 밖 getenv, inline 200행이라는 오래된 설명 | 설정 경계·운영 기준 불일치 | config로 읽기 이동, 실제 100행 설명 | 구현 완료 |
| F11 | P3 | frontend/components/ui import graph | 앱에서 사용하지 않는 scaffold 다수, lint 경고 4개; JS 약 1.08MB | 유지비/초기 번들 부담 | 대량 삭제·번들 재설계는 별도 작업 | 보류 |
| F12 | P2 | session_store.py / services/real/* / context-inspector.tsx | process memory 세션, real stub, 로컬 Prompt 저장 버튼 미연결 | 재기동 복원·실서비스·영속 편집 미지원 | 기존 정책/서비스 도입 작업 유지 | 보류 |

P0는 현재 코드의 경계 우회/원문 노출 테스트로 확인한다. 실 자격 증명이나 사내 데이터는 사용하지 않는다. 미사용 export 삭제보다 정상 기능의 오류 전파를 우선한다.

## 보호 계약과 호환성

- Request: message, conversation_id, fork_from_turn_id 유지. Backend null/생략은 None, 프론트는 optional을 생략; 빈 fork 문자열은 반드시 전송.
- 공개 AgentEvent의 6종과 type/content/tool_name/data 유지. SDK 내부 reasoning·MCP 이름·SDK session ID를 공개하지 않는다.
- 정상 done.data.turn_id, None/빈 문자열/알 수 없는 fork fallback 유지. ResultMessage.uuid는 anchor로 사용하지 않는다.
- error 후 done, 사용자 취소는 error로 변환하지 않음. 손상/조기 종료 SSE는 기존 error 이벤트로 처리한다.
- pp_session_scope는 결과 접근 범위이며 인증이 아니다. Result Store ID, inline/large_result, TTL, 비공개 경로 및 visualization marker/bar/line 유지.
- 새로운 필수 필드/이벤트/패키지 없음. 정상 요청·결과의 wire shape는 변경하지 않는다. 실패 SDK tool data는 기존 status/error/message 표현으로 정규화한다.
- assistant-ui External Store와 기존 완료 감사 결정을 유지한다. UI status는 공개 진행 이벤트이며 모델 reasoning이 아니다.

## 할당·순서·인수 조건

1. [Backend 실행 계획](../backend/plan/260915-full-stack-refactoring-plan.md): 오류 경계, 성공 anchor, 결과 접근 및 SQL 경계 회귀.
2. [Frontend 실행 계획](../frontend/plan/260915-full-stack-refactoring-plan.md): transport/state 회귀와 실제 결과 표시.
3. mock/fake 및 브라우저 회귀, 전체 pytest/build/lint/diff 검사 후 결과 기록.

각 Task는 먼저 실패 재현을 확인하고 해당 검증 통과 후 다음 Task로 간다. 계약을 확장할 필요가 생기면 구현을 보류하고 이 문서에 기록한다.

전체 인수 조건: 정상 응답/parts 순서/오류/취소/재시도/포크를 유지하고, 조기 EOF와 도구 실패를 성공으로 표시하지 않는다. 만료·다른 scope·catalog 외 테이블 접근이 차단된다. 실제 payload의 수치·요약이 표시된다. 신규 의존성과 사용자 변경 손실이 없다.

## 회귀 위험과 rollback

위험은 잘못된 종료 판정, retry의 fork anchor 손실, SDK tool 오류와 업무 오류의 혼동이다. 정상/오류/취소를 분리한 테스트로 고정한다. 문제가 발견되면 이번 Task diff만 되돌릴 수 있도록 계층별로 작게 수정하며, 사용자의 Todo 변경은 rollback 대상이 아니다. 이번 작업에서 commit/reset/checkout은 실행하지 않는다.

## 기준선

- Backend: `python -m pytest -q` → 194 passed, 5 deselected (4.70s).
- Frontend: `npm run build` → 통과(tsc 포함), JS 1,082.04 kB; 500 kB chunk 경고.
- Frontend: `npm run lint` → 오류 0, Fast Refresh 경고 4 (catalog-result/button/sidebar/tabs).
- 실제 provider E2E는 인증을 사용하지 않고 제외한다.

## 결론 및 Changes

- SDK 도구 실패 원문 노출과 카탈로그 외 테이블 조회 우회를 차단했다.
- 실패·취소 턴에 성공 anchor를 기록하지 않고, 정상 SDK Result 없이 종료되면 안전한 error/done으로 끝낸다.
- Result Store tool이 cleanup 주기와 무관하게 TTL/scope를 검사하고 삭제·손상된 결과를 안전한 오류로 반환한다.
- SSE malformed/미완성 프레임/조기 EOF/중복 done을 처리하고 정상 완료, Backend 오류, 연결 실패, 사용자 취소를 구분했다.
- retry가 사용자 질문을 중복 추가하지 않으며 동일 tick 중복 실행과 이전 요청 callback/cleanup을 차단한다.
- 실제 producer가 반환하는 숫자 KPI(0 포함), 결과 summary, simulation 목록, recipe와 mock RAG 본문을 표시한다.
- 공개 schema, 정상 request/response, Result Store·chart 계약을 유지했다. 필수 필드 추가나 breaking change는 없다. 기존 미커밋 Todo 두 줄도 유지했다.

### 변경 후 Architecture

```text
Composer / ActionBar
  → useAgentChat.runRequest (message/retry/controller 단일 소유)
  → sendChatMessage → FastAPI chat → run_agent → SDK wrapper → Tool → Service
  → AgentEventAdapter (SDK 오류 차단, 업무 status 일치)
  → SSE 직렬화 → chat-sse (envelope 검증)
  → chat-state.applyAgentEvent (순수 전이)
  → chat-runtime.convertMessage → External Store → 기존 UI
```

호출 계층을 추가로 재설계하지 않았다. 파싱·순수 변환만 분리하고 hook은
468줄에서 256줄로 줄었다. 줄 수 감소 자체보다 retry/stream 공통 실행 경로와
독립 회귀 테스트 경계가 주요 변화다. SDK 성공 결과 관측은 adapter가 담당하고
Agent가 정상 종료 후에만 session/anchor를 반영한다.

### 제거한 코드와 유지한 코드

- 사용되지 않던 `retryOf` 옵션과 새 턴/포크 실행의 중복 stream/failure 정리를 제거했다.
- `retryPrompt` state + retry context ref를 단일 retry context state와 파생 prompt로 바꿨다.
- runtime/card의 별도 오류 판정, database inline/large_result 분기의 SQL/note 중복 마크업을 제거했다.
- catalog 순수 helper를 컴포넌트 파일에서 분리해 해당 Fast Refresh 경고를 제거했다.
- 미사용 scaffold 파일, 세션 dummy, 커스텀 sidebar, 공식 Parts/Composer/ActionBar/Markdown은 유지했다. 파일 대량 삭제나 라이브러리 교체는 하지 않았다.

## Contract: 최종 공개 계약

### Request와 세션·포크

| 항목 | 변경 전후 / 호환성 |
| --- | --- |
| message | 문자열 유지; 브라우저는 composer 입력의 text를 전송 |
| conversation_id | 브라우저 대화 ID; SDK session ID와 분리. optional 생략 유지 |
| fork_from_turn_id | 생략/null → None으로 이어가기; 빈 문자열 → 새 대화; 알려진 ID → 기존 transcript anchor; 알 수 없는 ID → 안전한 error 경고 후 새 대화 fallback |
| done.data.turn_id | 정상 성공에 발급. SDK 실패/조기 종료에는 성공 anchor를 발급하지 않는 버그 수정 |
| resume_session_at | AssistantMessage/UserMessage transcript UUID만 사용; ResultMessage.uuid 제외 유지 |
| pp_session_scope | HttpOnly scope 쿠키와 fetch credentials include 유지. 인증·조직 권한 체계로 확장하지 않음 |

Frontend `sendChatMessage`는 내부 반환값을 `Promise<void>`에서
`Promise<"complete" | "failed" | "aborted">`로 바꿨다. 이 값은 wire payload가
아니며 유일한 앱 호출자인 hook도 함께 수정했다. `complete`는 transport가
정상 done을 받았다는 뜻이다. Backend `error` 이벤트의 메시지 오류 상태와
독립적이다. 순수 parser는 6종 event와 nullable 공개 필드를 검증하며 unknown
이벤트와 malformed JSON을 조용히 버리지 않는다. producer가 사용하지 않는
`[DONE]` 문자열은 공개 AgentEvent가 아니므로 유효 종료로 인정하지 않는다.

### AgentEvent / SSE

| Event | 발생 시점 | Payload | Frontend 처리 |
| --- | --- | --- | --- |
| text | SDK 공개 TextBlock/ Fake 답변 | content: string | 마지막 text part에 이어 붙임; tool 뒤에는 새 text part |
| status | 업무 tool 시작·완료·실패 또는 Fake 진행 | data.step/status/label | 동일 step upsert; 내부 reasoning 아님 |
| tool_call | 등록된 업무 tool 시작 | tool_name: 짧은 공개 이름 | 진행 단계 시작; tool_call_id나 args를 새로 만들지 않음 |
| tool_result | 업무 tool 결과 | tool_name, data: dict | 도착 순서대로 tool part 추가; purpose를 진행 상세에 연결; runtime/card 오류 판정 공유 |
| error | SDK 실행 실패, route 예외, fork fallback 경고, FE transport 실패 | 안전한 content; SDK tool 실패는 tool_result의 status/error 표현 | 메시지 error 보존; 첫 출력 전 transport 실패만 연결 배너/retry; 부분 출력은 남김 |
| done | 정상 완료 또는 오류 뒤 종료 | 성공 시 data.turn_id; 오류 종료는 data 없음/null | running만 complete로 전환; error/cancelled 유지; 중복/후속 이벤트 무시 |

SSE는 `data: <AgentEvent JSON>`과 빈 줄 프레임을 유지한다. UTF-8 chunk 분할,
LF/CRLF, 여러 data 라인과 주석을 처리한다. 조기 EOF와 미완성 마지막 프레임은
error/done으로 종료하며 사용자 취소는 오류 이벤트를 추가하지 않는다. 첫 done
후 reader를 취소·해제하므로 서버가 연결을 열어 두어도 UI 실행 상태가 끝난다.

### Result Store와 시각화

- ID, inline(100행 이하)/large_result, 저장 상한 500행, 샘플·통계 payload 유지.
- 원본 대용량 행과 parquet 경로는 Agent context/UI에 추가하지 않았다.
- get_result_summary/page의 TTL·삭제·손상 검사를 보강했다. 다른 scope는 기존 not-found 형태와 같게 반환하며 legacy unscoped 결과 호환은 유지했다.
- prepare_visualization, visualization GET, chart marker, bar/line, scope, TTL 및 UI 무집계 원칙 유지.
- SQL 문자열 guard에 더해 SQLite authorizer가 실제 참조 테이블을 검사한다. CTE·정상 인용 table은 허용한다. real 서비스는 기존 미구현 상태이며 provider 별 동등한 실행 경계 검증이 필요하다.

## assistant-ui 활용

기존 완료 감사의 External Store 선택과 공식 primitive 사용을 유지했다.
메시지 소유권은 hook에 두고, 불완전 종료는 기존 공식 MessageStatus/Error UI에
전달한다. 새 자체 composer/viewport/메시지 저장소나 deprecated API를 도입하지
않았다. tool 오류는 runtime의 isError와 카드가 같은 helper를 사용한다.

공식 [External Store 문서](https://www.assistant-ui.com/docs/runtimes/custom/external-store)의
외부 상태·capability callback 경계를 참고했으며 설치된 0.15.19의
`external-store-adapter.d.ts`와 실제 runtime callback 검증으로 호환성을 확인했다.
공식 [Message 문서](https://www.assistant-ui.com/docs/primitives/message)의 Parts/Error
구조도 유지했다. 이 작업은 완료된 감사 결정을 다시 수행하거나 되돌리는 작업이 아니다.

## Validation: 실제 실행 결과

| 실행 명령/검증 | 결과 | 주요 출력·한계 |
| --- | --- | --- |
| `cd backend && python -m pytest -q` (수정 전) | 성공 | 194 passed, 5 deselected |
| `cd backend && python -m pytest -q` (최종) | 성공 | 217 passed, 5 deselected, 5.86s; +23 회귀 |
| `cd frontend && npm test` | 성공 | Node 내장 테스트 27/27 (SSE 14, 상태/runtime 7, 결과 renderer 6) |
| `cd frontend && npm run build` | 성공 | tsc type check 포함, 3493 modules; JS 1,083.08 kB / gzip 330.95 kB |
| `cd frontend && npm run lint` | 성공(경고 있음) | 오류 0, 기존 Fast Refresh 경고 3: button/sidebar/tabs. 기준선 4개에서 1개 감소 |
| `/tests/chat-browser.html` (Playwright) | 성공 | React StrictMode + assistant-ui runtime 10/10, PASS, pageerror 없음 |
| 격리 fake Backend/Frontend 브라우저 관통 | 성공 | SQL/입력 검증/KPI/최종 답변/bar 차트, Skills API; 차트 loading/success/500→retry; 다른 scope 404 |
| 400px 및 1440px 화면 | 성공 | 400px scrollWidth=400, error overlay 없음; desktop screenshot 확인 |
| `git diff --check` 및 수정 문서 상대 링크 | 성공 | 상대 링크·파일명 및 사용자 Todo 변경 보존 확인 |

실행 중 확인된 실패는 숨기지 않고 구분했다. SDK/Agent 신규 테스트 5개,
Result tool/SQL 경계 12개, transport 6개, result renderer 5개 및 최초 browser
lifecycle 2개가 수정 전 문제를 재현했다. signature parity 테스트의 최초 실패
1개는 postponed annotation의 문자열/타입 표현 차이였으며 `eval_str=True`로
동일 타입을 비교하도록 고쳤다. SQL authorizer의 CTE COUNT에는 database=None
콜백이 발생해 정상 CTE 테스트로 보정했다.

검증 도중 export 이동으로 개발 서버 HMR의 오래된 catalogSummary import가
남았다. 이번 작업의 별도 개발 서버를 재시작한 뒤 새 로드에서 pageerror 없이
관통했다. Node 테스트 Vite 서버의 공통 WebSocket 포트 충돌은 테스트 파일을
직렬 실행하도록 설정해 제거했다. 오류 UI 검증용 500 응답은 의도한 주입이다.

### 회귀 시나리오와 증거

- 정상 text, text→tool→text, 여러 status/result: frontend chat-state/transport 및 fake API tests.
- Backend error→done, malformed/미완성 SSE, done 없는 종료, 중복 done: chat-api tests.
- 첫 출력 전 연결 실패, 부분 출력 후 오류, cancel, cancel 직후 새 요청: browser harness와 transport tests.
- edit/regenerate·재시도 fork anchor·첫 턴 빈 anchor: browser harness. 알 수 없는 ID fallback은 SDK query double을 사용하는 backend test_agent.
- client disconnect: ASGI http.disconnect를 보내 실제 StreamingResponse가 agent iterator를 닫는 test_api.
- inline/large_result 및 summary: test_services/test_tools와 results.test.mjs.
- marker loading/success/error/retry 및 다른 scope 차단: 브라우저 관통과 기존 visualization tests.
- mock/real 함수 signature parity: eval_str로 실제 타입을 해석한 test_services.

### 미실행과 한계

실제 Claude CLI/provider 인증 E2E 5개는 기본 pytest 설정대로 제외했다. 인증정보를
조회하거나 실제 모델을 호출하지 않았다. fake runner는 실제 SDK session 포크를
수행하지 않으므로 포크는 SDK double + 실제 frontend runtime으로 분리 검증했다.
real SQL/RAG/simulation 성공 payload parity는 아직 stub이라 실행할 수 없으며
함수 signature와 공통 validation 경계만 검증했다. Backend 별도 lint/type-check
설정은 없어 해당 명령을 만들지 않았다. 실제 폐쇄망 설치·반입 검증도 미실행이다.

## Remaining Issues

- F11: 앱에서 사용하지 않는 ui/sidebar, select, card 등 scaffold와 미사용 ToneText/RuleLabel, 3개 lint 경고는 유지했다. 대량 삭제는 요청 범위 밖이다.
- F11: 기존 Vite 500 kB 경고는 유지된다. 성능 계측 없이 의존성 교체·bundle 분할을 이번 결함 수정에 섞지 않았다.
- F12: session_store는 프로세스 메모리이며 persistence/multi-worker 공유를 제공하지 않는다. 실제 thread persistence 계약이 필요하다.
- F12: real service는 NotImplementedError stub이다. 실제 서비스/자격증명과 provider별 SQL 경계 검증이 준비되어야 구현할 수 있다.
- F12: Sidebar 세션·사용자, Metadata·Prompt는 로컬 데이터이며 Prompt 저장/설정 버튼은 미연결이다. 정책·저장 계약 확정 전 기능을 만들지 않았다.
- 진행 단계는 현재 step(tool 이름) 단위로 갱신된다. 병렬 동일 tool 호출을 개별 그룹화할 stable tool_call_id가 없다는 기존 보류 결정을 유지한다.

세부 변경 파일과 Task 실행 결과는 Backend/Frontend 실행 계획을 참조한다.


### 최종 race 보강 기록

같은 React 처리 주기의 cancel→append에서 오래된 render prefix가 이전 assistant를
running으로 복원하는 결함을 추가 재현했다. 일반 새 턴은 최신 React state에
functional update로 추가하며, retry는 남아 있는 원래 user를 재사용한다. 포크만
명시적 prefix를 사용한다. 동일 tick reset→append도 추가해 최종 브라우저
harness는 10/10 PASS다. 이 보정 후 npm test 27개, build/type check와 lint를
다시 통과했다.

## 변경 파일 목록 및 최종 작업 트리

아래는 `git status --short --untracked-files=all` 결과다. `M`은 수정, `??`는 신규 파일이다.
commit/push/reset/checkout 및 기존 파일 대량 삭제는 실행하지 않았다.
`plan/Todo.md`에는 기존 사용자 변경 두 줄이 함께 포함되어 있다.

```text
 M backend/agent/agent.py
 M backend/agent/event_adapter.py
 M backend/core/config.py
 M backend/services/mock/mock_sql_service.py
 M backend/tests/test_agent.py
 M backend/tests/test_api.py
 M backend/tests/test_event_adapter.py
 M backend/tests/test_services.py
 M backend/tests/test_tools.py
 M backend/tools/result_tool.py
 M backend/tools/sql_tool.py
 M frontend/AGENTS.md
 M frontend/README.md
 M frontend/docs/decisions.md
 M frontend/package.json
 M frontend/src/components/chat/tool-result-card.tsx
 M frontend/src/components/chat/tool-results/catalog-result.tsx
 M frontend/src/components/chat/tool-results/database-result.tsx
 M frontend/src/components/chat/tool-results/knowledge-result.tsx
 M frontend/src/components/chat/tool-results/result-summary.tsx
 M frontend/src/components/chat/tool-results/shared.ts
 M frontend/src/components/chat/tool-results/simulation-result.tsx
 M frontend/src/hooks/use-agent-chat.ts
 M frontend/src/lib/chat-api.ts
 M frontend/src/lib/chat-runtime.ts
 M plan/Todo.md
?? backend/plan/260915-full-stack-refactoring-plan.md
?? frontend/plan/260915-full-stack-refactoring-plan.md
?? frontend/src/components/chat/tool-results/catalog-data.ts
?? frontend/src/lib/chat-sse.ts
?? frontend/src/lib/chat-state.ts
?? frontend/src/lib/tool-result.ts
?? frontend/tests/chat-api.test.mjs
?? frontend/tests/chat-browser.html
?? frontend/tests/chat-browser.tsx
?? frontend/tests/chat-state.test.mjs
?? frontend/tests/results.test.mjs
?? plan/260915-full-stack-refactoring-plan.md
```
