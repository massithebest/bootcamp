# assistant-ui 전면 감사 및 리팩터링 계획

- 상태: 완료 (Task 1~6 구현·검증 완료, 2026-09-15)
- 작성일: 2026-09-15
- 상위 기준: [프로젝트 요구사항 및 Todo](../../plan/Todo.md)
- 대상 버전: `@assistant-ui/react@0.15.19`, `@assistant-ui/react-markdown@0.14.15`
- 범위: `frontend`의 assistant-ui Runtime, Thread/Message, Composer, Markdown, Tool UI, 진행 상태, 세션 목록 및 이관 잔재
- 비범위: 이번 계획 작성 단계의 소스 수정, 백엔드 `AgentEvent` 계약 변경, Runtime/전송 프로토콜 교체, Next.js 재도입

## 1. 결론

현재 구조의 큰 방향은 assistant-ui의 External Store 권장 모델과 맞는다. `use-agent-chat.ts`가 메시지와 SSE 수명주기를 소유하고 `useExternalStoreRuntime`이 이를 UI 상태와 액션으로 노출하며, `ThreadPrimitive.Viewport`, Composer, ActionBar, Markdown primitive를 범용 채팅 동작에 사용하는 경계도 적절하다. Vercel AI SDK나 assistant-ui 자체 스트림 프로토콜로 옮길 근거는 없다.

구현 전에 바로잡을 핵심은 세 가지다.

1. `ThreadPrimitive.Messages components`는 설치 버전 타입에서 명시적으로 deprecated이며 children render function으로 바꿔야 한다. `MessagePrimitive.Parts components`도 0.15.19에서 동작하지만 최신 공식 문서는 children API를 새 코드의 기본으로 안내한다.
2. `setMessages`는 단순 상태 setter가 아니라 branch switch와 message delete capability를 활성화한다. 현재 앱은 선형 대화만 유지하고 branch repository를 보존하지 않으므로 이 capability를 노출하지 않는 편이 현재 계약에 정직하다.
3. `convertMessage`가 백엔드 오류와 사용자 취소까지 `complete/stop`으로 변환한다. assistant-ui의 공식 `MessageStatus`와 `MessagePrimitive.Error`를 사용할 수 있도록 메시지의 종료 원인을 명시해야 한다.

Tool UI, Agent 진행 표시, Markdown 도메인 스타일, 데이터베이스/지식/카탈로그/시뮬레이션/차트 렌더러는 유지한다. 현재 백엔드 이벤트에 안정적인 `tool_call_id`, tool args, 호출-결과 상관관계가 없으므로 toolkit이나 `GroupedParts`로의 전면 전환은 기능 개선이 아니라 계약 변경이 된다. 커스텀 세션 목록도 아직 실제 persistence가 없고 External Store용 thread-list adapter가 설치 타입에서 active development/deprecated로 표시되므로 보류한다.

## 2. 감사 기준과 근거

### 프로젝트 제약

- Vite 7 + React 18 SPA를 유지한다.
- 메시지, 요청 실행, 취소, 편집/재생성 포크, 재시도는 `src/hooks/use-agent-chat.ts`가 소유한다.
- `useExternalStoreRuntime`과 기존 `fetch`/`ReadableStream` SSE를 유지한다.
- `ai`, `@ai-sdk/react`, `useChat`, AI SDK 스트림 프로토콜을 추가하지 않는다.
- 백엔드 `AgentEvent`의 공개 필드는 `type`, `content`, `tool_name`, `data`이며 assistant-ui 도입만을 이유로 변경하지 않는다.
- 폐쇄망 배포를 위해 새 패키지는 꼭 필요한 경우에만 추가한다.
- 도메인 결과 UI는 assistant-ui의 책임이 아니다.

### 확인한 공식 문서

- [External Store Runtime](https://www.assistant-ui.com/docs/runtimes/custom/external-store): 외부 상태 소유, `messages`/`isRunning`/`convertMessage`, `onNew`/`onEdit`/`onReload`/`onCancel`, `setMessages`의 역할
- [Migration to v0.14](https://www.assistant-ui.com/docs/migrations/v0-14): primitive의 `components` prop에서 children render function으로 이전
- [Thread primitive](https://www.assistant-ui.com/docs/primitives/thread): Viewport 자동 스크롤, Messages children API, `AuiIf`, ViewportFooter
- [Message primitive](https://www.assistant-ui.com/docs/primitives/message): Parts pipeline, tool UI resolution, `MessagePrimitive.Error`, children API
- [Message Part Grouping](https://www.assistant-ui.com/docs/guides/part-grouping): `MessagePrimitive.GroupedParts`가 실제 reasoning/tool-call part를 인접 그룹화하는 조건
- [Tool UI](https://www.assistant-ui.com/docs/tools/tool-ui): toolkit 등록, render-only backend tool, `toolCallId`/args/status 기반 렌더링
- [Markdown text element](https://www.assistant-ui.com/elements/markdown-text): `MarkdownTextPrimitive`의 message-part scope, GFM 및 component override
- [Threads](https://www.assistant-ui.com/docs/runtimes/concepts/threads): External Store의 멀티 스레드는 `ExternalStoreThreadListAdapter`와 외부 저장소 동기화가 필요

### 설치 버전 타입/API 근거

| 확인 항목 | 0.15.19/0.14.15 타입 근거 | 판독 |
|---|---|---|
| External Store callback | `node_modules/@assistant-ui/core/dist/runtimes/external-store/external-store-adapter.d.ts:124-147` | `onNew`, `onEdit`, `onReload(parentId, config)`, `onCancel`, `convertMessage` 모두 현재 사용 가능 |
| `messages`, `isRunning` | 같은 파일 `:71-102` | 외부 상태와 thread running 상태를 공급하는 공식 계약 |
| `setMessages` | 같은 파일 `:95-120`; 구현 `external-store-thread-runtime-core.js:162-169,358-366,406-423,476-511` | branch switch/delete를 활성화하고 cancel 시 draft 복원에도 관여하는 capability callback이지 일반적인 양방향 상태 동기화용 필수값이 아님 |
| 메시지 content/tool-call | `node_modules/@assistant-ui/core/dist/runtime/utils/thread-message-like.d.ts:9-48` | text part와 `tool-call`의 optional `toolCallId`, `args`, `argsText`, `result`, `isError`, metadata.custom 지원 |
| 메시지 status | `node_modules/@assistant-ui/core/dist/types/message.d.ts:290-302` | `running`, `complete(stop/unknown)`, `incomplete(cancelled/error/...)` 사용 가능 |
| Thread Messages | `node_modules/@assistant-ui/core/dist/react/primitives/thread/ThreadMessages.d.ts:40-51` | `components`는 타입에서 deprecated, children renderer는 정식 API |
| Message Parts | `node_modules/@assistant-ui/core/dist/react/primitives/message/MessageParts.d.ts:32-168` | `components`와 children 모두 현재 타입에 존재. `ToolGroup`, `ReasoningGroup`, legacy `ChainOfThought`만 타입에서 직접 deprecated; 공식 최신 문서는 새 코드에 children 권장 |
| GroupedParts | `node_modules/@assistant-ui/core/dist/react/primitives/message/MessageGroupedParts.d.ts:7-149` | 정식 API지만 실제 part와 안정적 grouping key가 있을 때 사용해야 함 |
| Suggestion | `node_modules/@assistant-ui/react/dist/primitives/thread/ThreadSuggestion.d.ts:25-54` | 현재의 `prompt` + `send`는 정식 API. deprecated인 것은 `autoSend`와 `method` |
| Markdown | `node_modules/@assistant-ui/react-markdown/dist/primitives/MarkdownText.d.ts:9-47` | `components`, `remarkPlugins`, `preprocess`, `smooth`, `defer` 지원. `unstable_memoizeMarkdownComponents`는 이름 그대로 unstable export |
| Thread list | `external-store-adapter.d.ts:21-42,148-158` | `ExternalStoreThreadListAdapter`는 존재하지만 핵심 switch API와 adapter slot에 active development/deprecated 표시가 있음 |

## 3. 현재 데이터 흐름

```text
ComposerPrimitive / Suggestion / ActionBar
                    │ onNew/onEdit/onReload/onCancel
                    ▼
use-agent-chat.ts ── 메시지·요청·AbortController·재시도·포크 소유
       │
       ├── chat-api.ts ── fetch + ReadableStream SSE ── Backend AgentEvent
       │
       └── convertMessage(chat-runtime.ts)
                    │ ThreadMessageLike
                    ▼
useExternalStoreRuntime → AssistantRuntimeProvider
                    │
                    ├── Thread/Message/Composer/ActionBar primitives
                    ├── MarkdownTextPrimitive
                    └── metadata.custom / tool-call result
                              ├── AgentProgress
                              └── ToolResultCard → domain result renderers
```

메시지 원본의 단일 소유자는 현재도 `use-agent-chat.ts`다. assistant-ui가 별도의 원본 메시지 배열을 소유하는 구조는 아니며, 내부 repository는 UI 기능을 위한 변환/파생 상태다. 다만 전역 요청 상태 `streaming`과 메시지별 `streaming`은 서로 다른 수명주기를 표현하면서 이름이 같고, 종료 원인이 없어 의미 불일치가 생긴다. 이후 계획에서는 전역 요청 상태와 메시지 상태를 명시적으로 구분한다.

## 4. 항목별 판정

| 우선순위 | 현재 파일/컴포넌트 | 현재 역할 | 공식 대안 | 판정 | 근거 | 변경 위험 |
|---|---|---|---|---|---|---|
| P0 | `lib/chat-runtime.ts` `convertMessage` | 앱 메시지를 `ThreadMessageLike`로 변환 | `MessageStatus`의 `running`/`complete`/`incomplete(cancelled,error)` 및 `MessagePrimitive.Error` | 개선 | 현재 오류·취소도 `complete/stop`이다. 설치 타입은 불완전 종료와 오류 payload를 지원한다. | 중간: 오류 배너, action bar 노출 시점, cursor 표현 회귀 가능 |
| P0 | `hooks/use-agent-chat.ts`의 `setMessages` | Runtime이 고친 메시지를 앱 상태로 반영 | 선형 모델에서는 생략; 분기 도입 시 repository와 함께 재설계 | 개선 | 0.15.19 구현에서 `setMessages`가 `switchToBranch`와 `delete` capability를 켠다. 현재 BranchPicker와 branch persistence가 없다. | 중간: 취소 시 composer draft 복원 동작을 반드시 회귀 검증 |
| P0 | `hooks/use-agent-chat.ts` messages/`isRunning`/callback | 외부 메시지와 실행 상태, 전송·취소·편집·재생성 연결 | 현행 `useExternalStoreRuntime` 계약 | 유지 | External Store 공식 용도와 정확히 맞고 각 callback signature도 설치 타입에 존재한다. | 낮음 |
| P1 | `chat-window.tsx` `ThreadPrimitive.Messages components` | 역할별 메시지/편집 composer 선택 | `ThreadPrimitive.Messages` children render function | 교체 | 공식 v0.14 migration과 설치 타입 모두 `components`를 deprecated로 표시한다. | 낮음: role 및 `message.composer.isEditing` 분기 누락 주의 |
| P1 | `thread-messages.tsx` `MessagePrimitive.Parts components` | Markdown과 tool-call override 렌더 | Parts children renderer에서 `part.type` 분기 및 `part.toolUI` fallback | 교체 | 0.15.19 타입은 아직 지원하지만 최신 공식 문서는 children을 새 코드의 기본으로 안내한다. | 중간: text/tool 도착 순서와 등록 Tool UI fallback 의미 유지 필요 |
| P1 | `thread-messages.tsx` `UserMessage` | 첫 번째 text part를 selector로 직접 추출 | `MessagePrimitive.Parts` + 사용자 text renderer | 교체 | 현재 코드는 첫 part만 표시한다. 공식 Parts pipeline은 모든 사용자 part를 순서대로 처리한다. | 낮음: 현행 whitespace 스타일 보존 |
| P1 | `thread-messages.tsx` ActionBar/EditComposer | 복사, 편집, 재생성, 편집 취소/저장 | 현행 `ActionBarPrimitive`, `ComposerPrimitive` | 유지 | callback capability와 공식 primitive 연결이 적절하며 수동 clipboard/edit state가 없다. | 낮음 |
| P1 | `chat-window.tsx` Viewport/ScrollToBottom | 자동 스크롤과 수동 하단 이동 | 현행 `ThreadPrimitive.Viewport`, `ScrollToBottom` | 유지 | 공식 Thread가 제공하는 viewport management를 이미 사용한다. 별도 scroll effect가 없다. | 낮음 |
| P1 | `message-input.tsx` Composer | 입력, Enter 전송, 실행 중 취소, disabled | 현행 Composer 유지; 조건부 표시는 선택적으로 `AuiIf` | 개선 | 입력/전송/취소는 공식 primitive에 위임되어 적합하다. `useAuiState`도 정식 API라 필수 교체는 아니지만 `AuiIf`가 조건 렌더 의도를 단순화한다. | 낮음 |
| P1 | `empty-state.tsx` Suggestion | 정적 예시 질문 즉시 전송 | 현행 `ThreadPrimitive.Suggestion prompt send` | 유지 | 설치 타입에서 현재 조합은 정식 API이며 deprecated props를 쓰지 않는다. runtime suggestion adapter는 동적 제안이 없으므로 과도하다. | 낮음 |
| P2 | `markdown-text.tsx` | GFM, 도메인 불릿 전처리, 제품 스타일 | 현행 `MarkdownTextPrimitive` + `remark-gfm` + overrides | 유지 | 공식 element의 확장 지점을 올바르게 쓴다. 기존 도메인 `·` 불릿 및 표/코드 스타일은 유지 가치가 있다. | 낮음 |
| P2 | `agent-progress.tsx` + AI Elements `ChainOfThought` | `status` AgentEvent의 업무 진행 단계 표시 | 공식 `GroupedParts`/reasoning UI | 유지 | statuses는 모델 reasoning/tool part가 아니라 `metadata.custom`의 도메인 이벤트다. GroupedParts로 바꾸면 의미와 입력 계약이 달라진다. | 중간: 이름이 비슷하다는 이유로 교체하면 진행 단계 손실 |
| P2 | `tool-result-card.tsx`, `tool-results/**` | 완료된 도메인 tool 결과를 표/차트/지식/시뮬레이션 UI로 표시 | 현행 Parts tool override; toolkit 전환은 보류 | 유지 | assistant-ui가 책임지는 것은 part 배치/registry이고 업무 payload 시각화는 앱 책임이다. 현재 override는 공식 확장 seam이다. | 낮음 |
| P2 | tool-call/result 변환 | 결과 도착 시 synthetic id로 완료 tool-call part 생성 | 공식 toolkit/Tool UI/status/GroupedParts | 보류 | 백엔드 `AgentEvent`에 stable `tool_call_id`와 args가 없고 병렬 호출의 call-result pairing도 노출되지 않는다. toolkit의 실행/승인/partial 상태를 정직하게 만들 수 없다. | 높음: 잘못 묶인 결과 또는 이중 tool 실행 가능 |
| P2 | `chat-api.ts` | fetch/ReadableStream 기반 SSE와 오류 정규화 | assistant-ui streaming/AI SDK protocol | 유지 | 현재 백엔드 계약에 맞고 Runtime 선택과 독립적이다. 공식 예제의 AI SDK transport는 이 프로젝트 제약과 맞지 않는다. | 높음: 교체 시 백엔드 전면 변경 필요 |
| P3 | `app-sidebar.tsx` | 앱 세션 목록/도구 흔적 UI, 현재 dummy 선택 상태 | `ExternalStoreThreadListAdapter` + ThreadList primitives | 보류 | 공식 thread-list는 외부 thread id, 목록, 전환, 메시지 hydration/persistence가 필요하다. 현재는 실제 저장 계약이 없고 설치 타입도 adapter를 active development로 표시한다. | 높음: thread id 불일치 시 다른 세션 메시지 노출 가능 |
| P3 | `ai-elements/task.tsx` | 이관된 Task 표시 컴포넌트 | 없음 | 제거 | 전역 import 검색 결과 사용처가 없다. 현재 진행 UI도 이 컴포넌트를 쓰지 않는다. | 낮음 |
| P3 | `ai-elements/chain-of-thought.tsx`의 Search/Image exports | 검색 badge와 이미지 보조 UI | 필요한 최소 local component만 유지 | 제거 | `AgentProgress`는 Root/Header/Content/Step만 사용한다. SearchResults/SearchResult/Image는 사용처가 없고 Badge 의존까지 끌어온다. | 낮음 |
| P3 | `ai-elements/tool.tsx` `getStatusBadge` export | 내부 ToolHeader 상태 표시 helper | 비공개 함수 | 개선 | 외부 사용처가 없으며 lint warning 1건의 원인이다. 컴포넌트 파일의 공개 표면을 줄일 수 있다. | 낮음 |
| P3 | Next.js/AI SDK 이관 잔재 | 과거 프레임워크/SDK 참조 여부 | 없음 | 유지 | `src`/package 검색에서 Next import, `use client`, `@ai-sdk`, `useChat`, `streamdown`이 없고 관련 패키지도 설치되지 않았다. 주석은 의도 기록이다. | 없음 |

## 5. 유지할 기능과 경계

다음은 리팩터링 과정에서 반드시 보존한다.

- 사용자 메시지 입력, Enter 전송, Shift+Enter 줄바꿈, 빈 입력 전송 방지
- 스트리밍 중 전송 대신 취소 버튼 노출 및 `AbortController` 취소
- SSE text/status/tool_call/tool_result/error/done 순서 처리
- text와 tool result의 도착 순서 보존
- 연결 실패 시 빈 assistant 제거, 사용자 메시지 유지, 재시도 배너 제공
- 편집/재생성 시 `turnId`를 이용한 백엔드 세션 포크
- 진행 중 cursor와 준비 중 문구, 완료 후 진행 블록 자동 접힘
- 복사, 편집, 재생성, scroll-to-bottom
- `·` 불릿 전처리, GFM 표/링크/코드 및 현재 Markdown 스타일
- database, knowledge, catalog, simulation, bar/line chart 및 generic fallback
- 카탈로그 기본 접힘, 오류 결과 표시, 미검증 표시
- 세션의 시간 그룹/도구 trace 표시와 3-pane 레이아웃
- 새 패키지 및 외부 런타임 리소스 없는 폐쇄망 동작

책임 경계는 다음과 같이 유지한다.

| 책임 | 변경 전 | 변경 후 |
|---|---|---|
| 원본 메시지와 실행 상태 | `use-agent-chat.ts` | 동일. 단, 요청 실행 상태와 메시지 종료 상태를 명확히 분리 |
| 네트워크/SSE | `chat-api.ts`, Backend `AgentEvent` | 변경 없음 |
| assistant-ui 연결 | `chat-runtime.ts` 변환 + hook의 External Store adapter | 동일. 실제 지원 capability만 노출하고 공식 status 의미를 사용 |
| 채팅 상호작용 | Thread/Message/Composer/ActionBar primitives | 동일. deprecated iteration API만 children API로 전환 |
| Markdown | `MarkdownTextPrimitive` + 프로젝트 override | 변경 없음 |
| 진행 상태 | metadata.custom → `AgentProgress` | 변경 없음 |
| 도구 결과 | tool-call result → `ToolResultCard` → 도메인 renderer | 변경 없음. toolkit은 계약 충족 전까지 보류 |
| 세션 목록 | 앱 상태 + `AppSidebar` | 변경 없음. 실제 persistence 설계 후 adapter 재평가 |

## 6. 실행 계획

각 Task는 별도 검증과 커밋이 가능한 크기다. 앞 Task의 검증이 끝나기 전 다음 Task를 섞지 않는다.

### Task 1 — deprecated 메시지 iteration 제거

- 수정 대상:
  - `src/components/chat/chat-window.tsx`
  - `src/components/chat/thread-messages.tsx`
- 변경:
  - `ThreadPrimitive.Messages components`를 children renderer로 바꾼다.
  - `message.composer.isEditing`, `message.role`을 기준으로 `UserEditComposer`, `UserMessage`, `AssistantMessage`를 선택한다.
  - `MessagePrimitive.Parts components`도 children renderer로 옮겨 `text`는 `AssistantText`, `tool-call`은 `part.toolUI ?? <ToolPart ...>` 순서로 처리한다.
  - 사용자 메시지의 첫 text part 직접 추출을 없애고 Parts pipeline으로 모든 text part를 표시한다.
- 선행 조건: 없음.
- 회귀 위험:
  - 편집 중 메시지가 일반 사용자 bubble과 동시에 보일 수 있음.
  - `null` 반환은 등록된 tool/data UI를 자동 렌더한다는 공식 의미가 있으므로, 의도적으로 숨길 part는 `<></>`를 반환해야 함.
  - text/tool part 순서가 변하면 안 됨.
- 검증:
  - `npm run lint`, `npm run build`
  - 사용자/assistant 메시지, 편집 진입/취소/저장, 복사/재생성 수동 확인
  - text → tool result → text 순서 fixture 확인
- 커밋 단위 예시: `refactor(frontend): migrate assistant-ui message render functions`

### Task 2 — External Store capability를 실제 앱 기능과 일치시키기

- 수정 대상:
  - `src/hooks/use-agent-chat.ts`
  - `src/lib/chat-runtime.ts`의 오래된 상태 소유권 주석
- 변경:
  - 선형 대화만 지원하는 동안 `setMessages`를 제거해 `switchToBranch`/`delete` capability를 광고하지 않는다.
  - `onNew`, `onCancel`, `onEdit`, `onReload`, `messages`, `isRunning`, `convertMessage`는 유지한다.
  - `chat-runtime.ts`의 상태 소유자가 `chat-window.tsx`라는 오래된 주석을 `use-agent-chat.ts`로 고친다.
  - 향후 branch 기능은 `setMessages` 하나만 복원하지 말고 branch repository/persistence/BranchPicker를 함께 설계한다는 주석을 남긴다.
- 선행 조건: Task 1 완료 권장. capability UI가 정상 노출되는지 확인하기 쉬워진다.
- 회귀 위험:
  - assistant-ui cancel의 trailing-user-to-draft 복원은 `setMessages`가 있을 때만 가능하다. 현행 앱은 user + 빈 assistant를 먼저 외부 상태에 넣고 자체 `handleStop`이 메시지를 보존하므로 기대 동작은 그대로지만 반드시 실제 취소 시나리오로 검증한다.
  - 숨겨진 message delete/branch 동작에 의존한 코드가 없는지 runtime state를 확인한다.
- 검증:
  - 전송 직후/첫 text 후/tool 실행 중 각각 취소
  - 취소 후 사용자 메시지와 composer 내용의 기대 상태 확인
  - 편집/재생성 capability가 계속 true이고 정상 작동하는지 확인
  - lint/build
- 커밋 단위 예시: `refactor(frontend): narrow external store runtime capabilities`

### Task 3 — 메시지 완료/취소/오류 상태를 공식 의미로 정규화

- 수정 대상:
  - `src/types/chat.ts`
  - `src/hooks/use-agent-chat.ts`
  - `src/lib/chat-runtime.ts`
  - `src/components/chat/thread-messages.tsx`
  - `src/components/chat/agent-progress.tsx` (필요한 최소 prop 변경만)
  - `src/lib/dummy.ts`
- 변경:
  - 전역 요청 실행 여부와 개별 assistant 메시지의 lifecycle을 구분한다.
  - 권장 모델은 개별 메시지에 `runState: "running" | "complete" | "cancelled" | "error"`와 오류 문구를 두고, 기존 message-level `streaming` boolean을 제거하거나 migration 동안 한 곳에서만 파생하는 것이다.
  - `convertMessage` 매핑:
    - running → `{ type: "running" }`
    - complete → `{ type: "complete", reason: "stop" }`
    - cancelled → `{ type: "incomplete", reason: "cancelled" }`
    - error → `{ type: "incomplete", reason: "error", error: message }`
  - 오류 표시는 custom metadata 기반 수동 조건 대신 `MessagePrimitive.Error` + `ErrorPrimitive.Root/Message`를 우선 사용한다. 진행 단계 목록은 계속 metadata.custom에 둔다.
  - `done`, `error`, fetch/parse 실패, 사용자 abort의 우선순위와 최종 상태 전이를 한 함수로 모은다.
- 선행 조건: Task 2 완료. cancel의 메시지 보존 정책이 확정되어야 한다.
- 회귀 위험:
  - 백엔드 `error` 후 `done`이 오더라도 error를 success로 덮어쓰면 안 됨.
  - 부분 출력 후 연결 실패와 무출력 연결 실패는 기존 UX가 다르므로 유지해야 함.
  - 취소 메시지의 기존 부분 출력은 남기되 cursor/running 상태는 끝나야 함.
  - error status에 JSON 직렬화 가능한 값만 넣어야 함.
- 검증:
  - 정상 완료, 무출력 연결 실패, 부분 출력 후 error, tool error, 사용자 cancel 네 경로 이상을 fixture 또는 hook test로 검증
  - assistant-ui state에서 message.status와 thread.isRunning 확인
  - 오류 block의 `role="alert"`, action bar 및 재시도 동작 확인
  - lint/build
- 커밋 단위 예시: `fix(frontend): preserve assistant message terminal states`

### Task 4 — Composer 조건 렌더 단순화

- 수정 대상:
  - `src/components/chat/message-input.tsx`
  - 선택 시 `src/components/chat/chat-window.tsx`
- 변경:
  - Send/Cancel 조건을 `AuiIf`로 표현해 직접 `useAuiState` 구독을 줄인다.
  - EmptyState 조건도 외부 `messages.length`와 assistant-ui thread state가 동일하다는 테스트가 확보된 경우에만 `AuiIf condition={(s) => s.thread.isEmpty}`로 통일한다.
  - ComposerPrimitive 자체, 입력 키보드 동작, disabled/canSend 판단은 변경하지 않는다.
- 선행 조건: Task 3 완료. thread running/empty 상태 의미가 먼저 안정화되어야 한다.
- 회귀 위험: `AuiIf` 조건을 반대로 작성하거나 Send/Cancel이 동시에 숨겨질 수 있음.
- 검증: 빈 입력, 입력 있음, running, cancel 직후 네 상태의 버튼과 키보드 동작 확인; lint/build.
- 커밋 단위 예시: `refactor(frontend): align composer conditions with aui state`

### Task 5 — AI Elements 미사용 잔재 최소 정리

- 수정/제거 대상:
  - 제거: `src/components/ai-elements/task.tsx`
  - 축소: `src/components/ai-elements/chain-of-thought.tsx`
  - 축소: `src/components/ai-elements/tool.tsx`
  - 조건부 제거: `src/components/ui/badge.tsx` (축소 후 import 0건을 다시 확인한 경우만)
- 변경:
  - 사용하지 않는 Task 전체와 ChainOfThought SearchResults/SearchResult/Image export를 제거한다.
  - `getStatusBadge`를 비공개 helper로 바꿔 해당 Fast Refresh warning을 제거한다.
  - 광범위한 `components/ui/**` 삭제는 하지 않는다. 폐쇄망에서 미리 반입한 로컬 소스라는 설계 의도가 있으므로 별도 inventory/정책 결정 없이는 잔재로 단정하지 않는다.
- 선행 조건: Task 1~4와 독립적이나 기능 리팩터링 후 수행하면 최종 import graph를 기준으로 판단할 수 있다.
- 회귀 위험: 동적 import나 향후 계획만으로 보관한 컴포넌트를 실수로 삭제할 수 있음. `rg`와 TypeScript build를 모두 통과해야 한다.
- 검증: import 0건 확인, lint warning 전후 비교, build, 진행 블록/tool card 수동 확인.
- 커밋 단위 예시: `chore(frontend): remove unused ai-elements surfaces`

### Task 6 — 회귀 검증 및 결정 기록 갱신

- 수정 대상:
  - `frontend/docs/decisions.md`
  - 자동화 도입 시 기존 테스트 위치 또는 새 `frontend` 테스트 경로
- 변경:
  - External Store capability, message terminal-state 매핑, tool/thread-list 보류 이유를 결정 기록에 반영한다.
  - 자동 테스트 기반이 없다면 새 패키지를 바로 추가하지 않고 우선 deterministic converter 단위 검증과 기존 lint/build, 브라우저 수동 시나리오를 체크리스트로 고정한다.
  - 테스트 패키지가 꼭 필요하다고 판단될 때만 폐쇄망 반입 비용과 lockfile 변경을 별도 승인 대상으로 기록한다.
- 선행 조건: Task 1~5 완료.
- 회귀 위험: 문서가 실제 구현과 어긋나는 것.
- 검증: 문서의 파일/API/버전 참조를 실제 코드와 재대조하고 전체 lint/build 실행.
- 커밋 단위 예시: `docs(frontend): record assistant-ui runtime boundaries`

## 7. 보류 항목의 재개 조건

### 공식 Tool UI/toolkit/GroupedParts

다음 조건이 모두 갖춰질 때 별도 설계로 재개한다.

- 백엔드가 각 호출에 stable `tool_call_id`를 주고 같은 id로 결과를 반환한다.
- tool args 또는 최소한의 렌더 schema를 공개할지 보안/계약 결정이 있다.
- 병렬/중첩 tool 호출의 순서와 상관관계가 정의된다.
- frontend tool 실행을 켜지 않고 render-only backend tool로 유지할지 결정한다.
- 기존 `ToolResult` payload와 database/knowledge/catalog/simulation/chart renderer를 그대로 연결할 migration adapter가 있다.

그 전에는 `MessagePrimitive.Parts`의 tool-call renderer seam과 현재 도메인 카드를 유지한다. AI Elements `Tool`은 presentational wrapper로만 사용하며 Vercel AI SDK를 추가하지 않는다.

### assistant-ui thread-list

다음 조건이 갖춰질 때 재평가한다.

- 실제 session list/load/create/switch/rename/archive/delete API와 권한 모델
- session별 message hydration과 진행 중 run 전환 정책
- `conversation_id`, assistant-ui thread id, backend session id의 단일 소유권
- 외부 store에서 thread별 messages를 보존하는 구조
- 현재 설치 버전의 `ExternalStoreThreadListAdapter` 안정성 재확인

그 전에는 `AppSidebar`를 제품 탐색 UI로 유지한다. 공식 primitive가 존재한다는 사실만으로 교체하지 않는다.

## 8. 제거 가능한 코드와 제거하지 않을 코드

즉시 제거 후보:

- `src/components/ai-elements/task.tsx`
- `chain-of-thought.tsx`의 사용하지 않는 SearchResults/SearchResult/Image와 그 전용 Badge 의존
- `tool.tsx`의 불필요한 `getStatusBadge` export
- `ThreadPrimitive.Messages components` 및 전환 후 불필요한 message component config 형태
- `UserMessage`의 첫 text part 직접 selector
- 검증 후 `useExternalStoreRuntime`의 불필요한 `setMessages`와 unsafe cast

유지:

- `use-agent-chat.ts`, `chat-runtime.ts`, `chat-api.ts`의 역할 분리
- `MarkdownTextPrimitive`, `remark-gfm`, 도메인 전처리/렌더 override
- AI Elements ChainOfThought의 실제 사용 subset과 Tool presentational wrapper
- 모든 `tool-results/**` 도메인 renderer와 chart fallback
- `AppSidebar`
- 문서/주석에 남은 Next.js, AI SDK 비도입 사유

## 9. 새 패키지 필요 여부

계획된 Task 1~6에는 새 패키지가 필요하지 않다. 현재 설치된 `@assistant-ui/react@0.15.19`, `@assistant-ui/react-markdown@0.14.15`, React, remark-gfm만으로 수행할 수 있다.

- `@assistant-ui/vite`, assistant-ui toolkit용 추가 build integration: 필요 없음
- `ai`, `@ai-sdk/react`, `useChat`: 도입 금지
- `streamdown`/Shiki: 필요 없음
- 테스트 runner: 현재 계획의 필수 의존성이 아님. 자동 hook/component test가 별도 승인될 경우에만 폐쇄망 반입 비용과 함께 제안

## 10. 검증 매트릭스

| 시나리오 | 확인 사항 |
|---|---|
| 새 질문 정상 완료 | user/assistant 순서, streaming cursor, done 후 complete/stop, 복사/재생성 |
| text-tool-text 응답 | part 도착 순서와 각 도메인 카드 유지 |
| tool error | tool card 오류 상태와 전체 message status를 혼동하지 않음 |
| backend error event | 부분 출력 유지, message incomplete/error, 접근 가능한 오류 표시 |
| 무출력 네트워크 실패 | 빈 assistant 제거, user 유지, 재시도 배너 |
| 전송 직후 취소 | AbortController 호출, thread.isRunning false, 메시지/draft 정책 유지 |
| tool 진행 중 취소 | 진행 블록 정지, 기존 결과/부분 출력 보존, incomplete/cancelled |
| 사용자 메시지 편집 | 편집 composer, 이전 이후 절단, 정확한 `fork_from_turn_id` |
| assistant 재생성 | 직전 user 재사용, 이후 응답 교체, 정확한 fork anchor |
| 빈 대화 suggestion | `prompt` 즉시 전송, 중복 메시지 없음 |
| 긴 대화 스크롤 | 사용자 스크롤 존중, 새 streaming 시 auto-scroll, ScrollToBottom 표시 |
| Markdown | GFM 표/목록/링크/코드와 `·` 불릿 유지 |
| 세션 전환/새 대화 | 기존 reset/abort/conversation id 정책 유지 |

정적 기준:

```bash
cd frontend
npm run lint
npm run build
npm ls @assistant-ui/react @assistant-ui/react-markdown --depth=0
```

감사 시점 baseline은 lint 0 errors/6 warnings, production build 성공이다. build에는 500 kB 초과 chunk warning이 있으나 assistant-ui 정확성 감사와 별도 성능 과제로 분리한다. Task 5 후 lint warning은 최소 2건(`tool.tsx`, 조건 충족 시 `badge.tsx`) 감소해야 하며 새 error/warning을 추가하지 않는다.

## 11. 추천 실행 순서

1. Task 1: deprecated children API 이전 — 저위험이며 이후 구조의 기준이 된다.
2. Task 2: External Store capability 축소 — 실제 지원 기능과 Runtime state를 일치시킨다.
3. Task 3: 종료 상태 정규화 — 가장 중요한 정확성 개선이며 별도 커밋/집중 검증한다.
4. Task 4: Composer/empty 조건 단순화 — 안정화된 runtime state 위에서 수행한다.
5. Task 5: 사용하지 않는 AI Elements 정리 — 최종 import graph를 기준으로 삭제한다.
6. Task 6: 전체 회귀 검증과 결정 기록 갱신.

Tool toolkit/GroupedParts와 thread-list는 위 순서에 넣지 않는다. 각각 백엔드 tool identity 계약과 세션 persistence 계약이 생긴 뒤 별도 계획으로 시작한다.

## 12. 실행 기록

구현자는 아래 표에 계획에 없던 판단, 공식 문서와 설치 타입 간 차이, 보류/범위 변경, 검증 결과를 Task별로 누적한다. 계획을 조용히 수정해 결과에 맞추지 말고, 최초 계획과 실제 판단의 차이를 남긴다.

| 일시 | Task | 관찰/문제 | 계획에 없던 판단 | 근거(코드·타입·문서) | 영향/후속 조치 |
|---|---|---|---|---|---|
| 2026-09-15 | 감사 baseline | lint 0 errors/6 warnings, build 성공, bundle size warning | bundle 최적화는 assistant-ui 감사 범위에서 분리 | `npm run lint`, `npm run build` | 리팩터링 후 동일 명령으로 비교 |
| 2026-09-15 | 감사 baseline | `MessagePrimitive.Parts components`는 설치 타입에서 허용되나 최신 문서는 children을 권장 | 즉시 장애가 아닌 forward-compatibility 교체로 P1 분류 | Message docs, v0.14 migration, 설치 `MessageParts.d.ts` | Task 1에서 동작 보존형 이전 |
| 2026-09-15 | 감사 baseline | External Store thread-list adapter가 공식 문서에는 있으나 설치 타입은 active development/deprecated | 현 세션 UI 교체를 보류 | Threads docs, 설치 `external-store-adapter.d.ts` | persistence 계약 수립 후 재검토 |
| 2026-09-15 | Task 1 | `ThreadPrimitive.Messages`/`MessagePrimitive.Parts`를 children renderer로 전환, `UserMessage`의 첫 text part 직접 추출 제거 | 계획대로 진행, 별도 이탈 없음 | 커밋 `57fdfc9` diff (`chat-window.tsx`, `thread-messages.tsx`) | Task 2 진행 가능 |
| 2026-09-15 | Task 2 | `use-agent-chat.ts`에서 `setMessages` 제거, `chat-runtime.ts` 상태 소유권 주석 갱신 | 계획대로 진행 | 커밋 `7ba5cf0` diff | Task 3 진행 가능 |
| 2026-09-15 | Task 3 | `types/chat.ts`에 메시지 terminal-state 도입, `convertMessage`가 `complete/incomplete(cancelled,error)`로 매핑, `dummy.ts` fixture 갱신 | 계획대로 진행 | 커밋 `0ad8961` diff (`chat.ts`, `chat-runtime.ts`, `use-agent-chat.ts`, `agent-progress.tsx`, `thread-messages.tsx`, `dummy.ts`) | Task 4 진행 가능 |
| 2026-09-15 | Task 4 | Send/Cancel 및 empty 조건을 `AuiIf` 기반으로 정리 | 계획대로 진행 | 커밋 `d47dace` diff (`chat-window.tsx`, `message-input.tsx`) | Task 5 진행 가능 |
| 2026-09-15 | Task 5 | `ai-elements/task.tsx` 제거, `chain-of-thought.tsx`의 미사용 export 제거, `tool.tsx`의 `getStatusBadge` 비공개화, 미참조된 `components/ui/badge.tsx` 제거 | 계획대로 진행 | 커밋 `945a7e2` diff | lint warning 6→4건 감소, 새 error 없음 |
| 2026-09-15 | Task 6 | Task 1~5가 계획된 커밋 단위(`57fdfc9`,`7ba5cf0`,`0ad8961`,`d47dace`,`945a7e2`)대로 완료돼 있음을 diff 재대조로 확인 | `frontend/docs/decisions.md`의 assistant-ui 절에 External Store capability 축소, 메시지 종료 상태 정규화, tool/thread-list 보류 사유 요약 반영. 자동 테스트 러너는 여전히 미도입 상태로 유지(§9 결정 유효) | `npm run lint` → 0 errors / 4 warnings(§10 baseline 6에서 예상대로 2건 감소), `npm run build` → 성공(500kB chunk 경고는 기존과 동일, 성능 과제로 분리) | 상위 [Todo.md](../../plan/Todo.md)의 해당 행 상태를 완료로 갱신 |
