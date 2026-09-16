# assistant-ui Elements 반입 소스

2026-09-16 공식 MCP 문서·Base 템플릿과 아래 registry 소스를 검토해 조정했다.
MIT 고지는 [../LICENSE](../LICENSE)에 포함한다. 파일은 복사 후 프로젝트가
관리하며 npm 패키지 업그레이드만으로 자동 갱신되지 않는다.

이 문서는 반입 출처와 Elements 조정 이력을 기록한다. 현재 애플리케이션 실행·
검증 방법은 [Frontend README](../../../../README.md), 제품 UI 규칙은
[Frontend 디자인 가이드](../../../../CLAUDE.md)를 기준으로 한다.

| 원본 registry | 반입 시 SHA-256 |
| --- | --- |
| https://r.assistant-ui.com/thread.json | `19374a0dde5fb240a2f0eab710fc0b6d1ffa62a40ee836edaea9b5ee94b462a2` |
| https://r.assistant-ui.com/elements-thread-list.json | `041e3f325f0937111b50eabc90c5487ba35cdaed7330f3fbe44c9fbacd93adf7` |
| https://r.assistant-ui.com/elements-tool-call.json | `810ee69b71c71507e951dbdebc5b08916a278e877e88eb774d8f8f4614fb0659` |
| https://r.assistant-ui.com/elements-agent-plan.json | `3e4767280e1e2f2b20d524d0795d5ad0399e7497dee7e485f9f5e91766073be6` |
| https://r.assistant-ui.com/tooltip-icon-button.json | `ef006b6ede556c09d0cd7974f7336c2d811d8c6efc5a77610d82683657bb66a2` |

## 조정 범위

- Thread: 기존 React 18 / assistant-ui 0.15.19 타입에 맞게 구현. attachment,
  dictation, Cloud, grouping, branch 탐색 등 계약에 없는 슬롯은 제외했다.
  한국어 입력·편집·액션과 기존 47.5rem 읽기 폭을 적용한다.
- TooltipIconButton: 공식 Base UI variant의 `render` 패턴을 사용한다.
  disabled/ref/이벤트는 실제 button에 전달하고 provider는 App에서 공유한다.
- ThreadList: stable id·한국어 그룹 이름을 받고 미연결 편집/삭제 장식을 제거한다.
- ToolCall: ReactNode 결과와 오류 표시를 추가한다. 호출 인자는 추측하지 않는다.
- AgentPlan: 단일 activeIndex 대신 명시적 상태를 받아 오류·중단·완료 미확인을 보존한다.
- surfaces: 필요한 semantic token만 사용한다. shimmer 패키지는 추가하지 않는다.
- MarkdownText: 기존 assistant-ui MarkdownTextPrimitive 렌더러를 이동했다.
  standalone 차트 Tool UI, 과거 chart marker와 코드/표의 스크롤 제한을 유지한다.

공식 Base UI variant: https://r.assistant-ui.com/styles/base-nova/tooltip-icon-button.json

전체 설계와 적용 예외는 [전환 계획](../../../../../plan/260916-assistant-ui-elements-plan.md),
[기술 결정](../../../../docs/decisions.md)을 참고한다.


## 공식 shadcn CLI 후속 설치

같은 날 사용자 요청으로 `npx shadcn@latest add @assistant-ui/thread @assistant-ui/thread-list`를
실행해 관련 소스를 추가했다. 기존 Thread/MarkdownText/TooltipIconButton은
덮어쓰지 않았다. `thread-list.aui.tsx`는 runtime 연결형, `thread-list.tsx`는
현재 예시 목록에 쓰는 props 기반 구현이다.

React 18 호환을 위해 reasoning ref를 forwardRef로 조정했다. TooltipIconButton은
side/variant/size를 지원하며 native disabled를 계속 보존한다. generated 소스의
혼합 export는 유지하므로 Fast Refresh lint 경고가 발생한다.


## Elements 카탈로그 추가 적용

공식 [Elements 목록](https://www.assistant-ui.com/elements#messages)과 MCP의
`error-state`, `edit-message`, `stopped-run`, `retrieval-chunks`, `prompt-library`
문서 및 standalone registry 소스를 확인했다. 다음 원본을 React 18·runtime
primitive·한국어·semantic token에 맞게 조정했다. 추가 npm 의존성은 없다.
PromptLibrary는 후속 UI 요청에서 제거했으며 아래 hash는 검토 이력이다.

| 원본 registry | 반입 시 SHA-256 |
| --- | --- |
| https://r.assistant-ui.com/elements-error-state.json | `1e659dfabb2d493edc148145a25d69f271066268888b5292e8b75ee21be738cb` |
| https://r.assistant-ui.com/elements-edit-message.json | `58390818c78d31271aad712bfc4ca99bcac1664bf4f28460478a0559cf1adceb` |
| https://r.assistant-ui.com/elements-stopped-run.json | `d234891263b986643007c8c4f8fb91e92ff984e8f34184c39fd39063c9eab2ca` |
| https://r.assistant-ui.com/elements-retrieval-chunks.json | `2bf1a79af8df5fcd9c2ccdbf9ce8b2ff24a69f251e1ff4185f43843b9a38d841` |
| https://r.assistant-ui.com/elements-prompt-library.json | `e28e15c078c261041e8078d4d5739a6db20b42d6964037d7f2db2b251972e2a3` |

- ErrorState: 제목·상세·실제 재시도 액션 슬롯. 오류 알림은 한 번만 전달한다.
- EditMessage: standalone textarea 대신 ComposerPrimitive를 쓰고 현재 이후의
  assistant 답변 수를 안내한다. 저장은 현 adapter의 suffix 교체 동작을 따른다.
- StoppedRun: 부분 답변은 기존 Parts에 보존하고 runtime Reload로 다시 실행한다.
  동작이 다른 Continue/Discard나 장식용 스트리밍 커서는 가져오지 않는다.
- RetrievalChunks: 실제 문서만 표시한다. 임계값·점수를 생성하지 않으며 0~1의
  유한한 관련도만 meter로 표시한다. 본문을 줄여 숨기지 않는다.
- PromptLibrary: 한 차례 적용 후 제거했다. 기존 EXAMPLE_QUESTIONS는 시작
  화면 Composer 아래의 `ThreadPrimitive.Suggestion` pill로 직접 전송한다.

## 홈페이지형 Composer와 Reasoning

공식 홈페이지와 Reasoning 문서를 다시 확인해 Composer를 둥근 단일 surface로
조정했다. textarea의 전역 focus outline을 해당 slot에서만 제거하고 form 외곽선
하나로 focus를 표시한다. 질문 모음과 키 안내는 제거했다.

설치된 `reasoning.aui.tsx`의 ReasoningRoot/Trigger/Content/Text를 공개 status
이벤트에 연결했다. 실행 중 자동으로 열리고 shimmer label과 새 단계가 갱신되며,
완료 후 접힌다. 이 내용은 모델 chain-of-thought가 아니라 Backend가 공개한 업무
단계다. 답변은 SDK partial text_delta가 기존 text part에 누적되어 스트리밍된다.

## 표 표시와 Composer 준비 중 제어

공용 DataTable과 assistant Markdown 표는 데이터 행을 최대 100개만 렌더링하고
전체 건수와 생략 건수를 안내한다. Composer 왼쪽 아래에는 첨부, 현재 모델
`GLM-5.3-Flash`, 추론 강도 `중간`이 보인다. attachment adapter와 실행 옵션
계약이 추가되기 전까지 세 제어는 준비 중인 비활성 UI로 유지한다.

## 중첩 Tool 실행 과정

`tool-group.aui.tsx`의 controllable Root/Trigger/Content를
`MessagePrimitive.GroupedParts`에 연결했다. 최종 답변 위에는 닫힌 `툴 N개 사용`
한 줄만 남고, 첫 번째 펼침에서 Tool 목록, 두 번째 펼침에서 각 호출의 Parameters와
Result를 보여준다. 실행 중에는 전체 그룹을 열어 진행 상황을 표시하고 완료 시
그룹과 개별 Tool을 자동으로 닫는다.

ToolCall은 실행 결과가 오기 전에도 표시하며 오류가 있어도 Parameters/Result
상세를 확인할 수 있다. 호출 입력과 결과의 연결에는 Backend의 stable
`tool_call_id`를 사용한다.
