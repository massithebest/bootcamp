# Agent Workbench UI/UX 감사 후속 개선 — Frontend

**상태: 감사 완료 · 범위 내 구현·검증 완료 · 후속 계약 검토 보류. 마지막 갱신: 2026-09-16.**

- 상위 계획: [UI/UX 감사·공유 계약·인수 조건](../../plan/260916-agent-workbench-ux-audit-plan.md)
- Backend 의존: [계약 검증·fixture·후속 검토](../../backend/plan/260916-agent-workbench-ux-audit-plan.md)
- 착수 조건: 최신 코드에서 해당 감사 사례를 재현하고 [Frontend 지침](../AGENTS.md)과
  [디자인 가이드](../CLAUDE.md)를 확인한다. 새 API 없이 독립 수정 가능하다.
  F01·F02·F12는 Backend fixture와 표시 기대를 맞춘 뒤 최종 인수한다.
- 범위: FE-01~06 구현·검증 완료. 서버 timing·실제 모델 설정·영속 저장은 비범위로 유지한다.

## 1. 구현 원칙과 작업 순서

assistant-ui 전체 교체를 계획하지 않는다. Provider/ExternalStoreRuntime, Thread,
Composer, Message 액션, Markdown, Tool UI 등록 구조를 유지한다.
`useAgentChat`의 앱 상태 소유권과 기존 SSE를 보존한다. 공통 조작은 기존 primitives·
Elements를 조정하고, 도메인 Tool/SQL/표/차트/Inspector는 필요한 커스텀 구현을 유지한다.
설치된 assistant-ui 타입·공식 문서로 호환성을 확인하며 새로운 디자인 라이브러리를 추가하지 않는다.

공유 계약은 상위 계획을 기준으로 하며 여기서 payload를 다시 정의하지 않는다.
서버 timing·실제 모델 설정·영속 대화 저장이 준비될 때까지 기다리거나 가상 값을 채우지 않는다.
`ui-ux-pro-max`는 접근성·상호작용 검증에 활용하되 기존 업무 밀도·토큰·레이아웃을
일괄 대체하지 않는다. 11/12/13/14px type scale과 중앙 읽기 폭·독립 스크롤이 기준이다.

| 순서 | 작업 묶음 | 주 책임 감사 ID | 우선순위 |
| --- | --- | --- | --- |
| FE-01 | 결과 정확성·대화 보호 | F01, F02, F08 | P1 |
| FE-02 | 핵심 조작·접근성 | F03, F05, F06, F07 | P1 |
| FE-03 | 반응형·상세 밀도 | F04, F16 | P1 / P2 |
| FE-04 | 상태 피드백 | F09, F11, F12 | P2 |
| FE-05 | 시간 표시 | F10 | P2 |
| FE-06 | 정보 구조·일관성 | F13, F14, F15, F17 | P2 / P3 |

F01~F17의 주 책임은 이 표에서 각각 한 번만 배분한다. 상태·포커스·시간 등
연관 검증은 함께 수행할 수 있지만 별도 감사 ID를 만들거나 원래 ID를 합치지 않는다.

## 2. FE-01 — 결과 정확성·대화 보호

- 감사 항목: F01, F02, F08
- 변경 대상: `src/lib/chat-runtime.ts`, `src/components/chat/thread-messages.tsx`,
  `src/components/chat/tool-result-card.tsx`, `src/components/chat/chat-window.tsx`,
  `src/components/chat/app-sidebar.tsx`, `src/hooks/use-agent-chat.ts`,
  `src/components/assistant-ui/elements/message-actions.aui.tsx`, 기존 편집 안내.
- 요구 동작:
  - F01: 성공한 standalone 표의 존재만으로 모든 Markdown 표를 제거하지 않는다.
    동일 데이터로 확인된 중복만 제거하며 별도 지표와 대응 관계가 없는 표는 남긴다.
    설명·fenced code·표/차트 앞뒤 문맥과 후속 조회 뒤 기존 결과를 보존한다.
  - F02: 그룹 헤더에 Tool 오류·미완료를 접힌 상태에서도 식별 가능하게 요약한다.
    턴 종료, Tool 성공, 복구된 오류를 분리한다. done이 오류를 성공으로 덮어쓰지 않으며
    과거 Tool 오류가 복구된 최종 답변을 무조건 실패로 만들지도 않는다.
  - F08: 이력 선택·현재 대화 교체·중간 답변 재생성 전에 영향 범위를 안내한다.
    필요한 경우 사라질 후속 메시지 수/범위를 표시하고 취소하면 대화·초안·선택을 보존한다.
    기존 편집 안내와 일관되게 하며 비영속 이력을 저장/복원 가능한 것처럼 표현하지 않는다.
- assistant-ui 적용: 기존 Message 액션·Reload/Edit 경로와 런타임 어댑터를 유지한다.
  별도 채팅 상태나 ThreadList 영속 런타임을 새로 만들지 않는다.
- 검증 방법:
  - `tests/chat-state.test.mjs`와 관련 렌더 테스트에 WIP standalone + 별도 불량률
    Markdown 표, 동일 표, 텍스트 뒤 늦은 표, 코드 펜스 표를 추가한다.
  - Backend BE-01~03 fixture로 오류→설명→done, 결과 누락→done,
    오류 후 후속 성공을 재현하고 열림/접힘 헤더와 개별 행을 비교한다.
  - 브라우저에서 사용자 6턴 후 이력 선택/취소, 중간 답변 재생성/취소,
    편집/새 채팅 및 관리 화면 왕복을 수행해 메시지·초안·fork 동작을 확인한다.
- 완료 조건:
  - [x] F01: 별도 표와 불명확한 대응 표는 보존되고 확인된 중복만 정책에 맞게 처리된다.
  - [x] F02: 오류·누락·복구 상태가 접힌 요약과 상세에서 일치한다.
  - [x] F08: 대화 교체 영향이 사전에 전달되고 취소 시 현재 작업이 그대로 남는다.
  - [x] 회귀 fixture와 브라우저 재현, 8절 공통 필수 검증 결과를 기록한다.

## 3. FE-02 — 핵심 조작·접근성

- 감사 항목: F03, F05, F06, F07
- 변경 대상: `src/components/assistant-ui/elements/message-actions.aui.tsx`,
  `src/components/assistant-ui/elements/markdown-text.tsx`,
  `src/components/assistant-ui/elements/thread.aui.tsx`,
  `src/components/chat/thread-messages.tsx`, `src/components/chat/tool-result-card.tsx`,
  `src/components/chat/tool-results/interactive-data-table.tsx`, `src/app/globals.css`.
- 요구 동작:
  - F03: 포인터 hover 없이도 키보드로 이전 메시지의 Copy/Edit/Reload에 접근한다.
    primitives는 유지하고 DOM에서 사라지는 autohide 정책을 조정한다.
    단순 focus-within 스타일 추가로 완료 처리하지 않는다.
  - F05: 중요한 메타·표 헤더·건수는 기존 semantic token으로 일반 텍스트 4.5:1 이상
    대비를 확보한다. 비활성 장식과 중요한 정보를 구별하고 모든 ink-3를 무조건 바꾸지 않는다.
  - F06: 긴 LOT·URL·inline code를 안전하게 줄바꿈한다. SQL/code fence와 표의
    내부 스크롤, mono·숫자 정렬은 보존한다. 전역 break-all은 사용하지 않는다.
  - F07: 완료 시 자동 접힘으로 숨겨지는 요소에 포커스가 있으면 보이는 그룹 trigger로
    돌린다. Composer 등 외부 포커스는 유지하고 자동 접힘과 사용자 수동 개폐의 우선순위를 기록한다.
- 검증 방법:
  - Tab/Shift+Tab/Enter/Space만으로 이전 메시지 액션·상세 조작을 수행하고 DOM 존재와 accessible name을 확인한다.
  - canvas/surface/surface-2별 실제 계산 색상으로 대비를 측정하고 focus-visible을 확인한다.
  - `LOT_` 120회·긴 URL·한글/영문 혼합·inline code를 1440px와 400px에서 확인한다.
    page scrollWidth뿐 아니라 실제 본문 잘림과 컴포넌트 scrollWidth/clientWidth를 검사한다.
  - 실행 중 내부 상세 trigger에 포커스 → done/error/cancel로 종료해 BODY로 유실되지 않는지 확인한다.
    외부 입력 포커스, 수동 개방 상세, 완료 후 재개방도 검사한다.
- 완료 조건:
  - [x] F03: hover 없이 모든 허용 메시지 액션에 키보드 접근이 가능하다.
  - [x] F05: 중요한 작은 텍스트의 배경별 대비 기준을 충족한다.
  - [x] F06: 긴 업무 문자열이 읽히며 코드/표 스크롤은 유지된다.
  - [x] F07: 숨겨지는 포커스만 복원하고 기존 자동 접힘·외부 입력을 방해하지 않는다.
  - [x] 브라우저 접근성 재현과 8절 공통 필수 검증 결과를 기록한다.

## 4. FE-03 — 반응형·상세 밀도

- 감사 항목: F04, F16
- 변경 대상: `src/components/chat/chat-window.tsx`,
  `src/components/assistant-ui/elements/thread.aui.tsx`, 기존 pane/Sheet UI,
  `src/components/chat/tool-results/database-result.tsx`,
  `src/components/chat/tool-results/catalog-result.tsx`.
- 요구 동작:
  - F04: Chat이 작업의 중심이 되도록 최소 사용 폭·패널 재개방 정책을 정한다.
    400px에서 고정 320px Inspector가 입력 공간을 80px로 압축하는 상태를 허용하지 않는다.
    기존 패널 접힘/열기와 필요 시 기존 Sheet를 검토하되 신규 라이브러리·별도 모바일 앱은 도입하지 않는다.
    패널 콘텐츠와 닫기 조작에 접근 가능하고 닫은 뒤 입력/포커스로 복귀할 수 있어야 한다.
    기존 downward threshold 전환·수동 선택 존중·접힌 패널 상태 보존을 회귀 검증한다.
  - F16: SQL/CTE는 기존 max-h-96 수준의 높이 제한과 내부 스크롤을 적용한다.
    SQL을 잘라 저장하거나 복사 내용을 생략하지 않는다.
- 검증 방법:
  - 1440, 1180, 1179, 860, 859, 768, 400px에서 축소/확대 왕복,
    양쪽 패널 각각/동시 재개방, Composer 다중 행 입력·전송·닫기를 확인한다.
  - 400px에서 입력·전송과 패널 닫기 버튼이 온전히 보이는지 측정한다.
    최소 폭 수치는 구현 전 실제 Composer 제어와 함께 결정·기록하며 임의 추정으로 확정하지 않는다.
  - 긴 SQL·CTE·100행 표·긴 응답으로 세 pane 독립 스크롤과 키보드 스크롤/전체 복사를 검사한다.
- 완료 조건:
  - [x] F04: 기본 자동 접힘과 수동 개폐 모두 입력 작업 폭·패널 접근성을 보장한다.
  - [x] F16: 상세 높이가 제한되고 전체 내용 읽기·복사가 가능하다.
  - [x] 경계별 실측, 선택한 패널 정책과 8절 공통 필수 검증 결과를 기록한다.

## 5. FE-04 — 상태 피드백

- 감사 항목: F09, F11, F12
- 변경 대상: `src/components/chat/thread-messages.tsx`,
  `src/components/chat/tool-result-card.tsx`,
  `src/components/chat/tool-results/database-result.tsx`, `src/app/globals.css`,
  필요한 경우 기존 `src/lib/chat-state.ts`의 상태 파생·테스트.
- 요구 동작:
  - F09: pending에서 Tool 실행·답변 작성·완료/오류/취소까지 안정적인 단일 polite
    알림 영역으로 의미 있는 전환을 전달한다. 타이머/토큰을 매번 읽지 않고
    interactive 상세 전체를 live 영역에 넣지 않는다. 기존 오류 alert와 중복 알림을 피한다.
  - F11: reduced-motion에서는 회전 대신 정적 아이콘+텍스트를 쓴다.
    일반 모드의 지속 spinner·공개 실행 안내는 기존 디자인 가이드대로 유지한다.
  - F12: 빈 assistant, SQL 0행 성공, 결과 없는 Tool 종료, 명시적 오류를 서로 다른
    상태로 표현한다. done만 수신한 경우에 성공 결과를 만들어내지 않는다.
    실제로 가능한 재시도만 제공하며 결과가 없는 빈 액션 줄도 검토한다.
- 검증 방법:
  - pending→동시 Tool→답변→done 및 error/cancel 경로에서 DOM/live 변화 횟수를 확인한다.
    실제 스크린리더가 가능한 환경에서 알림·중복 읽기를 별도 검증한다.
  - OS/브라우저 reduce 설정 양쪽에서 계산 animation과 화면 상태를 확인한다.
  - BE-02~03 fixture로 done-only, 0행, Tool 결과 누락, 오류→done,
    정상 내용과 standalone 결과만 있는 답변을 재현한다.
- 완료 조건:
  - [x] F09: 단계 변화는 전달되며 토큰·타이머·오류 알림이 중복되지 않는다.
  - [x] F11: 모션 감소 설정에서 무한 회전이 없고 진행 상태는 읽을 수 있다.
  - [x] F12: 빈 응답·0건·미완료·실패의 문구와 복구 조작이 구별된다.
  - [x] fixture 기반 브라우저 재현과 8절 필수 검증을 기록하며 실제 SR 미검증은 별도 명시한다.

## 6. FE-05 — 시간 표시

- 감사 항목: F10
- 변경 대상: `src/hooks/use-agent-chat.ts`, `src/lib/chat-state.ts`,
  `src/lib/chat-runtime.ts`, `src/types/chat.ts`의 프론트 로컬 상태,
  `src/components/chat/thread-messages.tsx`, `src/components/chat/tool-result-card.tsx`.
  참고 대상: `src/components/assistant-ui/elements/tool-fallback.aui.tsx`의 timing 사용.
- 요구 동작:
  - 실제 요청 시작부터 done/error/로컬 cancel까지 클라이언트가 관측한 대기 시간을 기록한다.
    “클라이언트 관측” 의미를 설명하며 서버의 순수 실행 시간으로 명명하지 않는다.
  - Tool 시간은 동일 tool_call_id의 호출 수신부터 결과 수신까지 실제 관측한 값이 있을 때만 표시한다.
    결과 누락·중단은 “Tool 완료 시간”으로 확정하지 않는다. 서버 실행 종료 확인과 로컬 취소는 다르다.
  - 설치 버전의 `useToolCallElapsed`/message timing 지원과 어댑터 연결 방식을 확인한다.
    사용하지 않는 ToolFallback을 시간 표시만을 위해 전체 교체하지 않는다.
  - 접힌 그룹 헤더에 전체 관측 시간을 보조 정보로, 개별 Tool 시간은 펼친 상세에 표시한다.
    실제 측정값이 없는 과거 메시지는 숨긴다. 메시지 ID에서 시간을 역산하거나 임의 값을 채우지 않는다.
  - 실행 중에는 작은 전용 표시 컴포넌트만 초 단위로 갱신하고 종료 후 고정한다.
    1초 미만 표시는 생략 또는 “1초 미만”으로 정책을 통일한다. tabular-nums와 기존 type scale을 쓴다.
    타이머를 live 알림에서 제외하고 Thread 전체를 매초 재렌더링하지 않도록 검증한다.
  - 서버 timing 계약은 Backend 보류 검토이며 본 Task의 선행 조건이 아니다.
- 검증 방법:
  - 제어 가능한 clock/이벤트 fixture로 done/error/cancel, 중복 종료·늦은 이벤트,
    재시도·reset·새 요청, 동시 Tool의 독립 시간과 측정 누락을 검증한다.
  - 브라우저에서 긴 대기→완료/취소, 탭 비활성화 후 복귀, 완료 후 접힘/열기를 확인한다.
    표시 누적은 실제 관측 기준으로 계산하고 interval 횟수를 실제 경과 시간으로 간주하지 않는다.
  - 타이머 해제·음수 방지·접근성 반복 읽기·렌더 범위를 확인한다.
- 완료 조건:
  - [x] 실제 클라이언트 관측 시간만 표시되고 서버 실행 시간과 의미가 분리된다.
  - [x] 종료/취소/reset 뒤 타이머가 정리되고 늦은 이벤트로 완료 시간이 변조되지 않는다.
  - [x] 측정값 없는 과거 메시지·Tool에 가짜 시간이 표시되지 않는다.
  - [x] 시간 테스트·브라우저 재현과 8절 공통 필수 검증 결과를 기록한다.

## 7. FE-06 — 정보 구조·일관성

- 감사 항목: F13, F14, F15, F17
- 변경 대상: `src/components/chat/tool-results/chart-block.tsx`,
  `src/components/chat/context-inspector.tsx`, `src/components/chat/chat-window.tsx`,
  `src/components/assistant-ui/elements/markdown-text.tsx`,
  `src/components/assistant-ui/elements/thread.aui.tsx`, `src/components/chat/tool-result-card.tsx`.
- 요구 동작:
  - F13: 검증된 기존 chart.data를 이용해 축·단위·실제 값을 읽을 수 있는 접이식
    표/데이터 대안을 제공한다. 다른 집계나 없는 값을 계산해 만들지 않는다.
    기존 Recharts 키보드 기능을 조사·보존하며 제목만으로 값 대안을 충족했다고 보지 않는다.
  - F14: Inspector 탭별 검색·필터·필요한 스크롤 상태를 세션 내 보존한다.
    기존 role/tab keyboard와 read-only 카탈로그 성격을 유지한다. 실행 trace와 혼동시키지 않는다.
  - F15: Chat main, 패널의 접근 가능한 이름, 답변 제목 계층과 탐색 순서를 정한다.
    필요 시 skip navigation을 기존 구조에 추가한다. heading 의미를 위해 시각적 글자 크기를 키우지 않는다.
  - F17: disabled 모델/추론 제어에 준비 중·설정 미연결 이유를 분명히 표시한다.
    실제 서버 모델을 아는 것처럼 label하지 않는다. Details 등 10px 레이블을 기존 type scale에 맞춘다.
    모델 선택/설정 API는 만들지 않는다.
- 검증 방법:
  - bar/line 다계열 차트의 데이터 대안과 실제 값·축·단위를 비교하고 키보드로 개폐한다.
    가능한 환경에서 실제 스크린리더/tooltip 탐색을 추가 검증한다.
  - 지식에서 wip 검색→도구→지식, 패널 접기/열기, 관리 화면 왕복 후 검색·스크롤과 초안을 확인한다.
  - DOM landmark 이름·heading 계층과 키보드 영역 이동을 확인한다.
  - 준비 중 label/설명과 계산 font-size를 확인하고 좁은 화면에서도 안내를 읽을 수 있는지 검사한다.
- 완료 조건:
  - [x] F13: 차트와 동등한 실제 값 대안이 있으며 키보드로 접근 가능하다.
  - [x] F14: 탭 이동·패널 조작 후 필터가 유지되고 기존 탐색이 정상이다.
  - [x] F15: 시각적 밀도를 유지하면서 주요 영역·제목의 의미 있는 탐색이 가능하다.
  - [x] F17: 미연결 기능이 실제 설정으로 오인되지 않고 type scale이 일관된다.
  - [x] 브라우저 재현과 8절 공통 필수 검증, 남은 보조 기술 검증 한계를 기록한다.

## 8. 구현 후 공통 검증과 보고

각 Task는 해당 재현 시나리오와 함께 아래 필수 검증을 수행했다.
감사 기준선과 구현 후 새 실행 결과를 구분한다. 결과와 미검증 범위는 9절에 기록한다.

```bash
cd frontend
npm test
npm run build
npm run lint
```

- [x] `tests/chat-browser.html`의 기존 lifecycle·실행 표시 회귀를 다시 실행하고 변경 항목의 재현을 추가한다.
- [x] `tests/knowledge-browser.html`의 기존 관리 회귀를 다시 실행해 공유 셸·포커스·초안 보호를 확인한다.
- [x] loading/empty/error/success/cancel, 부분 응답, keyboard/focus/label,
  표·차트 fallback과 상위 계획의 반응형 경계를 실제 브라우저로 검증한다.
- [x] 변경한 Task별 코드/fixture·브라우저 폭·조작·기대/실제 결과·명령 결과와 남은 경고를 기록한다.
- [x] 실제 LLM·스크린리더·모바일 가상 키보드·대규모 대화 성능은 실행한 항목만 통과로 기록한다.
  미실행이면 이유·남은 확인 항목을 명시한다.
- [x] 상위 계획·이 실행 계획·Todo의 완료 상태를 실제 구현/검증 범위에 맞게 함께 갱신한다.

## 9. 결정·실행 기록

- 2026-09-16: F01~F17을 6개 작업 묶음에 배분했다. 기존 primitives·Elements와
  업무용 디자인을 유지하고 결과 정확성·대화 보호를 먼저 수행하기로 계획했다.
- Backend 새 API를 기다리는 Task는 없다. 표/결과 fixture의 공동 인수는 필요하며,
  새 계약이 필요해지면 상위 계획을 먼저 갱신한다.
- 감사 기준선: 채팅 브라우저 11개·지식 관리 5개 통과 기록은
  [상위 감사 기록](../../plan/260916-agent-workbench-ux-audit-plan.md)에 보존한다.
### 구현 결과

| Task | 구현·결정 | 새 검증 근거 |
| --- | --- | --- |
| FE-01 | chat-runtime의 보수적 표 대응, execution-summary의 오류/누락 집계, 셸·Reload의 사전 확인 | workbench.test.mjs의 표/7개 종료 사례; 브라우저 별도 표·오류/누락·대화/초안·재생성 취소; 기존 fork 회귀 |
| FE-02 | ActionBar autohide=never, 중요 메타 ink-2, 본문 overflow-wrap:anywhere, use-execution-disclosure | hover 없이 이전 액션 DOM/키보드 접근, LOT_ 120회 줄바꿈, 헤더 색상, done 시 그룹 trigger 포커스 |
| FE-03 | 860/1180 아래 비모달 overlay, SQL/CTE max-h-96·tabIndex | 경계 축소/확대, 400px 재개방 입력창 334px, Escape/Shift+Tab, SQL 150줄 원문/높이 |
| FE-04 | 안정적 execution-announcement, reduce 정적 아이콘, 빈 응답·0건·미완료 분리 | 상태 영역 동일 노드, 오류/종료 fixture, 일반/reduce 계산 animation |
| FE-05 | 로컬 ObservedTiming·ObservedDuration; 요청과 같은 ID Tool 수신 간격 | monotonic clock, 완료/취소 고정, 과거/누락 시간 미합성, live 알림에서 타이머 제외 |
| FE-06 | 차트 원본 데이터 표, 탭 유지 mount, main/aside·h2~h6, 준비 중 label | 실제 차트 값 A/20, wip 필터 왕복, heading 구조, 모델 미연결 label |

- 새 파일: [execution-summary](../src/lib/execution-summary.ts),
  [관측 시간](../src/components/chat/observed-duration.tsx),
  [자동 접힘 포커스](../src/hooks/use-execution-disclosure.ts),
  [Markdown 제목 정규화](../src/lib/markdown-headings.ts).
- 회귀 파일: [단위/렌더 회귀](../tests/workbench.test.mjs),
  [브라우저 회귀](../tests/workbench-browser.tsx), [실행 진입점](../tests/workbench-browser.html).
  기존 chat-browser·knowledge-browser는 대화 삭제 확인을 승인하도록 테스트 환경에서만 confirm을 제어한다.
- 표 중복 판정은 컬럼·전체 행이 정확히 일치하는 단순 셀에만 적용한다.
  서식/escape/값 의미가 모호하면 보존한다. 백엔드 fallback의 마지막 결과와 다른 지표의 표를 혼동하지 않는다.
- 대화 교체와 재생성은 브라우저 기본 확인창으로 영향·복원 불가를 설명한다.
  취소 시 상태를 바꾸지 않으며 신규 Dialog 라이브러리는 추가하지 않았다.
- 패널은 기존 DOM을 유지하는 비모달 overlay다. 열 때 패널 조작으로 이동,
  Escape/닫기에는 여는 버튼으로 복귀, Tab 이탈에는 패널을 닫되 외부 포커스는 유지한다.
  자동 임계값 접힘은 아래로 통과할 때만 적용하고 확대 시 자동 재개방하지 않는다.
- 그룹·개별 Tool은 기존 자동 접힘을 유지하며 숨겨질 내부 포커스만 trigger로 이동한다.
  완료 뒤 사용자의 수동 열기는 다음 실행 상태 변경 전까지 유지한다.
- 설치된 assistant-ui timing은 현재 ExternalStoreRuntime의 서버 관측 계약을 자동 제공하지 않는다.
  useToolCallElapsed로 렌더 시점부터 가상 시간을 만들지 않고 실제 관측값을 metadata로 전달한다.
  작은 표시 컴포넌트만 초 단위 갱신하고 전체 Thread 상태를 매초 갱신하지 않는다.
- ui-ux-pro-max의 접근성·단계적 공개 기준을 사용하되 새 테마/폰트/패키지는 도입하지 않았다.
  [활성 디자인 결정](../docs/decisions.md)과 [디자인 가이드](../CLAUDE.md)에 후속 정책을 반영했다.

### 구현 후 실행 결과

- `npm test`: **66개 통과** (신규 workbench 단위/렌더 12개 포함).
- `npm run build`: 성공. 기존 대형 chunk 경고(500kB 기준, 약 1.30MB bundle)는 남았다.
- `npm run lint`: 오류 0, 기존 Fast Refresh 경고 13개. 새 경고 없음.
- 기존 채팅 **11개**, 기존 지식 관리 **5개**를 구현 후 다시 실행해 통과했다.
- 신규 Workbench **9개**를 1440×900 일반 모션과 400×900 reduced-motion에서 각각 통과했다.
  전체 App에 제어된 SSE/fetch를 연결했으며 실제 provider·운영 쓰기는 사용하지 않았다.
- 1440/1180/1179/860/859/768/400px 경계 왕복에서 가로 overflow 없음.
  400px Inspector 재개방 시 Chat 400px/입력창 334px, Inspector 320px을 확인했다.
- 실제 키보드로 이전 질문 복사에서 Tab → 편집, 400px 패널에서 Shift+Tab → Composer 복귀·닫힘을 확인했다.
- 실제 스크린리더·모바일 가상 키보드·LLM·수백 턴 성능·백그라운드 탭 장시간 실행은
  미검증이다. 바탕 clock 기반 시간 계산과 타이머 해제는 코드·단위/브라우저로 확인했다.
  6턴 이력·모든 차트 계열·전체 색상 조합의 수동 검증을 완료했다고 주장하지 않는다.
  공통 상태/데이터 경로를 fixture로 검증했으며 운영 인수에서 추가 확인한다.

## 10. 후속 정책: 화면 전환 확인창 제거

- 상태: 구현·검증 완료 (2026-09-16).
- 상위 범위: 상위 계획 9절의 사용자 요청으로 F08 중 화면 전환 확인만 대체한다.
- 변경 대상: chat-window.tsx의 새 채팅·예시 세션 확인 제거,
  workbench-browser.tsx의 확인 호출 0회·초안 초기화·세션 선택 완료 회귀.
- 유지: 재생성 확인, 지식 편집 미저장 보호, 세션 reset/fork와 Sidebar 안내.
- 검증: npm test/build/lint, Workbench 및 지식 관리 브라우저 회귀.
- 완료 조건: 대화와 초안이 있어도 전환을 막는 확인창이 없고 나머지 보호 동작이 유지된다.
- 실행 결과: npm test 66개 통과, build 성공, lint 오류 0·기존 경고 13개.
  Workbench 브라우저 9개와 지식 관리 5개 통과(1280px).
  새 채팅/예시 세션 확인 호출 0회, 초기화/선택 완료, 재생성 취소와 미저장 보호를 확인했다.
  최초 브라우저 실행은 자동 실행과 수동 실행 중복으로 fixture가 충돌해 실패했으며,
  페이지당 자동 실행 한 번으로 다시 실행해 통과했다. 기존 대형 bundle 경고는 남아 있다.

## 11. 후속 기능: Context Inspector 너비 조절

- 상태: 구현 완료 (2026-09-16). 실제 브라우저 수동 검증은 브라우저 제어 환경 부재로 보류.
- 변경 대상: `src/components/chat/chat-window.tsx`, `tests/workbench-browser.tsx`,
  `CLAUDE.md`의 3-pane 기준.
- 구현: Inspector 좌측에 focus 가능한 vertical separator를 두고 포인터 capture 기반
  드래그와 `←/→`, `Shift+←/→`, `Home/End`, 더블클릭 기본값 복원을 제공한다.
  드래그 중 body cursor·selection 변경은 effect cleanup으로 원복한다.
- 폭 정책: 기본 20rem/넓은 화면 23rem, 사용자 범위 16~35rem. 비-overlay에서는
  Sidebar를 포함한 현재 viewport에서 Chat 32.5rem을 먼저 보장하며, overlay에서는
  viewport 우측 기준 3rem 여백을 남긴다. 사용자 지정은 현재 App 세션에만 유지한다.
- 접근성: `role=separator`, vertical orientation, 최소·최대·현재 값과 픽셀 설명,
  visible focus를 제공한다. 드래그에 의존하지 않는 키보드 대안을 유지한다.
- 검증: `npm test` 67개 통과, `npm run build` 성공, `npm run lint` 오류 0·기존
  Fast Refresh 경고 13개. Workbench 브라우저 fixture에 separator semantics,
  방향키 확대, Home 최소화, 더블클릭 복원을 추가했다.
