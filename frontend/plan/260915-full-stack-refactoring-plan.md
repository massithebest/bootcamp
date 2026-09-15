# 전체 시스템 리팩토링 frontend 실행 계획

**상태: 완료. 마지막 갱신: 2026-09-15.**

- 상위: [전체 시스템 계획](../../plan/260915-full-stack-refactoring-plan.md)
- 상대 파트: [실행 계획](../../backend/plan/260915-full-stack-refactoring-plan.md)
- 착수 조건: 기존 지침·활성 계약·기준선 분석 완료. 공유 payload는 상위 계약을 따른다.

## Tasks

### F1. SSE transport 경계

- 대상: src/lib/chat-api.ts, parser 모듈, tests 및 무의존성 실행기.
- 이유/동작: envelope 검증, chunk/CRLF/data 라인, malformed/EOF/done 처리, abort 유지.
- 선행: 상위 F01. 위험: Backend error→done과 fallback warning 흐름 보존.
- 검증/완료: Node 내장 테스트 + 기존 TypeScript/Vite로 정상·손상·중복 done·부분 오류 검증.

### F2. 대화 lifecycle와 이벤트 변환 분리

- 대상: src/hooks/use-agent-chat.ts, src/lib/chat-state.ts, src/lib/chat-runtime.ts, tests.
- 이유/동작: 상태 소유권 유지, 순수 이벤트 변환 분리, retry 시 user 재사용, controller 기반 중복/늦은 callback 차단.
- 선행: F1 통과. 위험: edit/regenerate fork anchor, reset 직후 seed 오염.
- 검증/완료: runtime callback을 통한 retry/cancel→new/edit/regenerate 및 순서/MessageStatus 회귀.

### F3. 기존 tool payload 표시

- 대상: src/components/chat/tool-result-card.tsx, tool-results/*.tsx 및 parser helper.
- 이유/동작: 오류 판정 공유, 숫자 KPI와 요약/목록/recipe/mock RAG 표시.
- 선행: Backend producer 감사 완료, F2 통과. 위험: inline/large_result/기존 RAG 형태 호환.
- 검증/완료: 실제 payload fixture 렌더 검사, chart marker loading/success/error, build/lint.

### F4. 관통 검증과 문서

- 대상: 실행 계획, README(테스트 명령), Todo 및 상위 결과.
- 이유/동작: fake backend와 브라우저로 실제 사용 흐름 확인, 미실행 provider 검증 구분.
- 선행: F3. 위험: 기존 실행 중 서버와 사용자 변경 침범 방지.
- 검증/완료: 전체 build/lint, pytest 결과와 diff 검사 기록.

## 결정·실행 기록

- 2026-09-15: 소스 수정 전 계획 작성. 새 의존성·protocol 교체 없이 실패 재현과 점진 수정 진행.

### 완료 Task와 회귀

- [x] F1: chat-sse.ts로 프레임/envelope 파싱 분리. nullable 공개 필드 검증, malformed/EOF 실패 처리, 첫 done 후 reader 취소/해제 및 후속 이벤트 차단.
- [x] F2: chat-state.ts로 순수 변환 분리. runRequest가 전송/포크/재시도의 단일 실행 경로. retry context 하나에 원래 user/prefix/fork 보관. controller identity로 callback/cleanup 보호.
- [x] F3: tool-result.ts의 공통 오류 판정, 숫자 KPI(0 포함), summary/시뮬레이션 목록/recipe/mock RAG 표시. DB note/SQL 중복 마크업 제거. catalog helper 분리.
- [x] F4: Node 내장 테스트 실행 명령과 브라우저 harness 문서화. 기존 assistant-ui 컴포넌트 및 상태 소유권 유지.

`sendChatMessage`의 내부 return outcome은 Backend error 이벤트와 transport 실패를
구별한다. 정상 empty done은 완료로 남고, 첫 출력 전 연결 실패만 retry banner로
전환한다. 부분 출력은 error 상태와 함께 남는다. error→done의 error 상태는
assistant-ui `incomplete/error`로, cancel은 `incomplete/cancelled`로 유지된다.

추가 테스트 및 재현:

- tests/chat-api.test.mjs: 14개. UTF-8 byte 분할, CRLF, multi-data, 정상·Backend error, malformed envelope, 미완성/조기 EOF, terminal done, open connection, network/abort, request payload.
- tests/chat-state.test.mjs: 7개. 불변성/순서/진행/purpose/turnId, error/cancel/complete, runtime/card tool 오류 판정.
- tests/results.test.mjs: 6개. 숫자 KPI, summary, simulation list, 두 RAG 형식, recipe, inline/large_result.
- tests/chat-browser.tsx 및 chat-browser.html: StrictMode + 실제 assistant-ui runtime 10개. 동일 tick 중복 전송, Backend error, retry 사용자 중복, empty done, cancel→new, 동일 tick cancel/append 및 reset/append, edit/regenerate/retry fork, reset, 부분 오류.
- browser harness는 dev URL `/tests/chat-browser.html`에서 자동 실행한다. PASS/FAIL과 각 결과가 표시되고 production build 진입점에서는 참조하지 않는다.

실제 검증 결과:

- 수정 전 build 통과; lint 오류 0/경고 4.
- transport 테스트 최초 6개 실패, renderer 최초 5개 실패, browser 최초 2개 실패로 기존 결함 확인 후 보정.
- 최종 `npm test`: **27 passed / 0 failed**. 추가 라이브러리 없이 Node test + 설치된 Vite SSR 변환 사용.
- 최종 `npm run build`: **통과**, tsc 포함. JS 1,083.08 kB / gzip 330.95 kB. 기존 500 kB 경고 유지.
- 최종 `npm run lint`: **오류 0, 기존 경고 3** (button/sidebar/tabs). catalog-result의 경고 1개 제거.
- Playwright로 `/tests/chat-browser.html`: **10/10 PASS**, pageerror 없음.
- 별도 fake Backend(8015)/Frontend(3015): 정상 SQL·KPI·입력 관계·bar chart·Skills 조회 확인. 지연 응답 loading, 500 오류 후 retry(총 GET 2회), 다른 scope 404 확인.
- 400px에서 문서 scrollWidth 400, desktop 1440px screenshot 확인. UI 구성·스크롤 구조 유지.
- 개발 중 catalog helper export 이동으로 생긴 HMR stale import는 자체 dev 서버 재시작 후 해소. 실제 관통 새 로드에서 pageerror 없음.

assistant-ui 결정:

- External Store와 공식 Composer/Message.Parts/ActionBar/Error/Markdown 유지.
- 새 runtime/toolkit/GroupedParts/thread-list adapter를 도입하지 않음.
- 설치된 @assistant-ui/core 타입과 실제 runtime callback으로 호환성 검증.
- 상태/요청은 hook, parser·순수 전이는 lib, 도구 오류 판정은 공통 helper로 책임 분리.

변경 파일:

- src/hooks/use-agent-chat.ts
- src/lib/chat-api.ts, chat-sse.ts(신규), chat-state.ts(신규), chat-runtime.ts, tool-result.ts(신규)
- src/components/chat/tool-result-card.tsx
- src/components/chat/tool-results/catalog-result.tsx, catalog-data.ts(신규), database-result.tsx, knowledge-result.tsx, result-summary.tsx, shared.ts, simulation-result.tsx
- tests/chat-api.test.mjs, chat-state.test.mjs, results.test.mjs, chat-browser.tsx, chat-browser.html(신규)
- package.json(test script), README.md, AGENTS.md(현재 테스트 설명), docs/decisions.md, 본 실행 계획

미사용 scaffold 파일의 대량 삭제, bundle 분할, 로컬 세션/Prompt 영속화는 이번
구현에서 제외했다. 실제 provider 포크는 Backend query double로 검증했으며
CLI 인증을 사용하는 관통 E2E는 미실행이다.

### 최종 race 보강 기록

같은 React 처리 주기의 cancel→append에서 오래된 render prefix가 이전 assistant를
running으로 복원하는 결함을 추가 재현했다. 일반 새 턴은 최신 React state에
functional update로 추가하며, retry는 남아 있는 원래 user를 재사용한다. 포크만
명시적 prefix를 사용한다. 동일 tick reset→append도 추가해 최종 브라우저
harness는 10/10 PASS다. 이 보정 후 npm test 27개, build/type check와 lint를
다시 통과했다.
