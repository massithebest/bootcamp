# Agent Workbench UI/UX 감사 및 후속 개선 계획

**상태: 감사 완료 · 범위 내 구현·검증 완료 · 후속 계약 검토 보류. 마지막 갱신: 2026-09-16.**

- 프로젝트 기준: [Todo](Todo.md)
- 실행 계획: [Frontend](../frontend/plan/260916-agent-workbench-ux-audit-plan.md), [Backend](../backend/plan/260916-agent-workbench-ux-audit-plan.md)
- 디자인 기준: [프론트 가이드](../frontend/CLAUDE.md)

## 1. 목표·범위·비범위

생산계획 담당자가 답변과 근거 결과를 정확하게 읽고, 실행 상태와 복구 방법을
판단하며, 키보드와 작은 화면에서도 작업을 잃지 않는 업무용 Agent Workbench를 만든다.
이 문서는 기존 UI/UX 감사 F01~F17을 보존하고 개선 작업을 배분한다.
최초 문서화 이후 사용자의 구현 요청에 따라 Frontend FE-01~06과 Backend BE-01~03을 구현·검증했다.
서버 timing·실제 모델 설정·영속 저장은 승인된 범위 밖으로 계속 보류한다.
아래 감사 요약과 F01~F17은 수정 전 기준선이며, 구현 결과는 8절에 별도로 기록한다.

`ui-ux-pro-max`의 접근성·상호작용·반응형 검토 기준과 assistant-ui의 구성·상태
경계를 적용했다. 일반적인 디자인 권고보다 사용자의 제약, 저장소 지침,
기존 제품 계약과 semantic token을 우선한다.

- 기존 assistant-ui primitives·Elements, ExternalStoreRuntime와 SSE 구조를 유지한다.
- Sidebar / Chat / Context Inspector의 업무용 정보 구조와 dense한 가독성을 유지한다.
- semantic color, 시스템 폰트, 기존 type scale·간격·테마·스크롤 규칙을 우선 재사용한다.
- 신규 디자인 라이브러리, 외부 CDN·폰트·런타임 API를 임의로 도입하지 않는다.
- 랜딩페이지형 장식, 전체 UI 재작성, 별도 모바일 내비게이션 제품 구축은 제외한다.
- 실제 모델 설정 조회, 대화 영속 저장·분기 복원, 서버 실행 시간 계약은 후속 검토다.
- 기존 완료 계획은 해당 시점의 이력으로 유지한다. 이 감사는 추가 재현 조건에 대한
  후속 범위이며 이전 계획의 완료 상태를 되돌리지 않는다.

## 2. 감사 요약

### 강점과 assistant-ui 사용 판단

- Provider와 `useExternalStoreRuntime` 연동은 적절하다. 앱의 `useAgentChat`이
  메시지·SSE·취소·편집·재생성을 소유하고 assistant-ui가 렌더링·조작을 담당한다.
- Thread Viewport/Footer/ScrollToBottom, Composer Input/Send/Cancel, 메시지 액션,
  Markdown slots, GroupedParts와 등록된 Tool UI를 활용하고 있다.
- standalone 표·차트의 답변 문맥, 원본 건수·잘림 안내, 표 검색·정렬·페이지 이동은 유지 가치가 높다.
- 메시지 오류·재시도, 부분 응답 취소 후 보존, 공개 실행 안내와 작업 종료 후 상세 접힘이 이미 존재한다.
- Context Inspector의 도구·스킬·지식 설명과 읽기 전용 상세, 지식 관리의 변경 이탈 안내는 적절하다.

assistant-ui 전체 교체는 필요하지 않다. 커스텀 실행 그룹·Tool 결과·SQL·도메인 지식
상세·Result Store·Recharts/TanStack 결과는 도메인 역할이 있어 유지한다.
Copy/Edit/Reload 등 기존 primitives의 표시 정책과 어댑터의 결과 처리만 보완한다.
시간은 설치 버전의 timing 기능과 연결 가능성을 검토하되 실제 관측값이 없으면 표시하지 않는다.
범용 disclosure·탭은 기존 UI 컴포넌트 재사용 대상으로, assistant-ui 전용 컴포넌트로
무조건 대체하지 않는다. 영속 런타임 없는 Sidebar에 ThreadList 연결을 가장하지 않는다.

### 우선 해결할 문제 5개

1. 성공한 standalone 표 하나 때문에 무관한 Markdown 표도 제거되어 정보가 사라진다(F01).
2. Tool 실패·미완료와 턴 종료를 구별하지 않는 실행 그룹 요약이 성공으로 오해될 수 있다(F02).
3. 이력 선택·재생성에 따른 현재 대화 교체·후속 메시지 제거 안내가 부족하다(F08).
4. 키보드 액션 접근, 자동 접힘 포커스, 핵심 메타 정보 대비가 부족하다(F03·F05·F07).
5. 좁은 화면에서 패널 재개방 시 입력 작업 폭이 무너지고, 긴 식별자가 잘린다(F04·F06).

### 상태별 UX matrix

| 상태·재현 조건 | 감사 당시 동작 | 개선 또는 유지 기준 |
| --- | --- | --- |
| 빈 대화 | 환영·예시·Composer 제공 | 기존 즉시 전송 동작 유지 |
| 요청 후 첫 Tool 전 | pending 실행 안내와 status 표시 | 기존 안내 유지, 지속 상태 영역과 연결(F09) |
| 공개 계획 pending/running | AgentPlan 표시 경로 존재 | 실제 서버 queue나 퍼센트로 추정하지 않음; 일부는 코드 검토만 수행 |
| Tool 실행 중·동시 2개 | 그룹 자동 열림, 개별 진행 표시 | 동시 Tool은 각각 진행으로 유지; 실제 부모/자식 실행 계약은 없음 |
| 상세 열기 | 그룹 → 호출 상세의 단계적 공개 | 중첩 disclosure를 실제 실행 계층으로 단정하지 않음 |
| Tool 결과 수신 | 요약과 상세·standalone 표/차트 표시 | 별도 표 보존(F01), 결과 읽는 문맥 유지 |
| Tool 결과 없이 종료 | 개별 미완료 표시 가능 | 상위 요약도 누락을 반영(F02·F12) |
| 답변 작성 중 | 실행 그룹 안내·spinner와 텍스트 | 기존 공개 안내 지속, 정상 모션 유지 |
| 정상 완료 | 그룹 자동 접힘과 최종 답변 | 접힘 시 숨겨지는 포커스 복원(F07) |
| Tool 오류 후 텍스트와 done | 그룹 성공형 종료 요약 | 턴 종료와 Tool 결과를 구분; 복구된 오류도 사실대로 표시(F02) |
| 백엔드 오류 | 안전한 오류·재시도 제공 | 내부 예외 미노출과 기존 복구 흐름 유지 |
| 응답 전 통신 실패 | 오류 안내·같은 사용자 입력 재시도 | 사용자 메시지 중복 없이 유지 |
| 부분 응답 후 오류 | 수신한 부분 보존 | 결과·Tool 문맥을 지우지 않고 오류 안내 |
| 사용자 취소 | 부분 응답 보존·재시작 | 이어받기인 것처럼 표현하지 않음 |
| 편집·재생성 | 기존 fork 식별자와 대화 절단 동작 | 편집 안내 유지, 재생성 영향 안내 추가(F08) |
| done만 수신 | 내용 없는 assistant와 액션 가능 | 빈 응답·실패·미완료를 구별(F12) |
| SQL 성공 0행 | 본문이 비어 보이는 경로 | “조회 결과 0건”과 빈 응답을 구별(F12) |
| 표·차트 로딩/오류 | 개별 처리 경로 존재 | 준비 실패·빈 데이터까지 일관된 구분 유지 |
| Sidebar 이력 선택 | 비영속 안내는 있으나 현재 대화 reset | 교체 영향 안내·취소 시 보존(F08) |
| Inspector 탭 이동 | 탭 키보드 조작 제공, 검색 상태 소실 | 카탈로그와 실행 trace 구별, 탭 상태 보존(F14) |

### 반응형 실측

단위는 CSS px이다. 넓은 화면에서 좁은 화면으로 내려가며 측정한 기본 상태이며,
패널은 임계값 아래에서 자동 접힌다. 모든 작은 화면 동작이 실패한 것은 아니다.

| viewport 폭 | Sidebar | Chat | Inspector | 관찰 |
| --- | --- | --- | --- | --- |
| 1440 | 248 | 872 | 320 | 기본 3-pane |
| 1180 | 248 | 612 | 320 | Inspector 유지 경계 |
| 1179 | 248 | 931 | 0 | Inspector 자동 접힘 |
| 860 | 248 | 612 | 0 | Sidebar 유지 경계 |
| 859 | 0 | 859 | 0 | Sidebar 자동 접힘 |
| 768 | 0 | 768 | 0 | 기본 입력 가능 |
| 400 | 0 | 400 | 0 | 기본 입력 가능 |
| 400, Inspector 수동 재개방 | 0 | 80 | 320 | textarea clientWidth 14; F04 |

지식 관리 상세는 400px에서 페이지 폭 400px, 목록 복귀 조작을 확인했다.
긴 LOT 식별자는 문단 scrollWidth 4010px에 비해 문단 폭이 데스크톱 760px,
400px 화면에서 368px여서 내용이 잘렸다(F06). 페이지 자체 가로 스크롤이 없다는
사실만으로 통과시키지 않는다. 경계 왕복·패널 수동 조작·실제 콘텐츠까지 재검증한다.

## 3. 감사 항목 F01~F17

P1은 결과 신뢰·대화 보호·필수 조작, P2는 상태 이해·접근성 보강·작업 효율,
P3는 후속 일관성 우선순위다. 예상 범위의 소/중은 상대 작업량이며 일정 확정이 아니다.
근거의 행 번호는 감사 시점 참고값이다. 구현 착수 시 최신 코드에서 재현하고
이미 해결된 항목은 새 검증 근거로 판정한다. 감사 결과를 최신 구현 완료의 증거로 쓰지 않는다.

### F01 — 별도 Markdown 표 소실

- 심각도·영향: P1. 서로 다른 지표 표가 사라져 분석 결과 일부를 읽을 수 없다.
- 근거: [chat-runtime.ts](../frontend/src/lib/chat-runtime.ts), 160·173행 부근. 성공한 `prepare_table`이 하나라도 있으면 답변 전체에 `removeMarkdownTables` 적용.
- 재현: WIP standalone 표 성공과 별도 불량률 Markdown 표가 같은 응답에 있을 때 후자가 사라짐.
- 개선: 데이터 대응 관계가 확인된 중복만 제거하고 불명확하거나 별도 지표인 표는 보존한다.
- 예상 범위·확신도: 중, 높음(브라우저·코드). Frontend 어댑터·회귀 테스트, Backend 자동 보완 조건 검증.

### F02 — 실행 그룹의 성공 오인 요약

- 심각도·영향: P1. 도구가 실패하거나 결과가 누락돼도 전체 성공처럼 보인다.
- 근거: [thread-messages.tsx](../frontend/src/components/chat/thread-messages.tsx), 125·137~154행 부근. 턴 `isComplete` 중심 헤더.
- 재현: Tool 오류 → 설명 텍스트 → done에서 접힌 그룹에 녹색 체크와 “응답 작성 완료 · 툴 1개 사용”.
- 개선: 종료 여부와 개별 Tool 결과를 분리해 오류·미완료를 요약한다. 복구된 오류를 무조건 최종 답변 실패로 바꾸지 않는다.
- 예상 범위·확신도: 중, 높음(브라우저·코드). Frontend 집계·표시, Backend 종료 시나리오 검증.

### F03 — hover 전용 메시지 액션

- 심각도·영향: P1. 마우스 없이 이전 메시지 편집·복사 등에 접근하기 어렵다.
- 근거: [message-actions.aui.tsx](../frontend/src/components/assistant-ui/elements/message-actions.aui.tsx), 10행 부근. `autohide="not-last"`; 설치 패키지의 hover 판단으로 액션 DOM이 제거됨.
- 재현: 포인터가 이전 메시지 밖에 있는 상태에서 Tab만으로 편집·복사 진입 시도.
- 개선: Copy/Edit/Reload primitives를 유지하되 키보드 접근 가능한 표시 정책으로 변경한다. unmount된 액션은 CSS `focus-within`만으로 해결되지 않는다.
- 예상 범위·확신도: 소, 높음(DOM·설치 라이브러리 확인). Frontend 독립.

### F04 — 패널 재개방 시 Chat 폭 붕괴

- 심각도·영향: P1. 좁은 화면에서 입력·전송 작업 공간이 사실상 사라진다.
- 근거: [chat-window.tsx](../frontend/src/components/chat/chat-window.tsx), 123행 부근. 고정 폭 패널과 중앙 최소 작업 폭 정책 부재.
- 재현: 400px에서 Inspector 수동 재개방 → Chat 80px, textarea clientWidth 14px.
- 개선: Chat 최소 사용 폭과 패널 우선순위를 정의하고 기존 패널/Sheet 수단으로 접근성을 보존한다.
- 예상 범위·확신도: 중, 높음(실측). Frontend 독립, 별도 모바일 제품 구축 제외.

### F05 — 핵심 메타 정보 대비 부족

- 심각도·영향: P1. 표 헤더·원본 건수·중요 보조 정보 판독이 어렵다.
- 근거: [globals.css](../frontend/src/app/globals.css), 26행 부근과 [interactive-data-table.tsx](../frontend/src/components/chat/tool-results/interactive-data-table.tsx), 117·141행 부근.
- 재현: ink-3 `#8b939e`와 흰 배경 3.10:1, surface `#f6f7f9` 2.90:1, surface-2 `#eceef1` 2.67:1.
- 개선: 기존 ink-2 또는 의미에 맞는 token으로 일반 중요 텍스트 4.5:1 이상 확보. 비활성 예외를 일반 메타 정보에 적용하지 않는다.
- 예상 범위·확신도: 소, 높음(색상 계산·사용처). Frontend 독립. 기준: [WCAG 대비](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

### F06 — 긴 식별자·문자열 잘림

- 심각도·영향: P1. LOT·경로·링크 등 업무 식별자의 일부가 숨겨진다.
- 근거: [markdown-text.tsx](../frontend/src/components/assistant-ui/elements/markdown-text.tsx), 43·189행 부근과 [thread.aui.tsx](../frontend/src/components/assistant-ui/elements/thread.aui.tsx), 35행 부근. wrapping 부족과 viewport overflow-x-hidden.
- 재현: `LOT_`를 120회 반복한 문단, 데스크톱과 400px에서 내용 잘림.
- 개선: 본문·링크·inline code는 안전하게 줄바꿈하고 코드 블록·표는 내부 가로 스크롤을 유지한다.
- 예상 범위·확신도: 소, 높음(브라우저·코드). Frontend 독립; 전역 break-all은 피한다.

### F07 — 자동 접힘 뒤 포커스 소실

- 심각도·영향: P1. 실행 중 상세를 키보드로 읽다가 완료되면 탐색 위치를 잃는다.
- 근거: [thread-messages.tsx](../frontend/src/components/chat/thread-messages.tsx), 133행 부근과 [tool-result-card.tsx](../frontend/src/components/chat/tool-result-card.tsx), 103행 부근. 종료 시 자동 접힘.
- 재현: 실행 중 Tool 상세 trigger에 포커스 → done → `document.activeElement`가 BODY.
- 개선: 자동 접힘으로 숨겨지는 포커스를 보이는 그룹 trigger로 복원한다. 외부 포커스는 빼앗지 않고 수동 열기 정책을 명시한다.
- 예상 범위·확신도: 소, 높음(브라우저). Frontend 독립; 기존 자동 접힘 기본 동작 유지.

### F08 — 대화 교체·절단 영향 안내 부족

- 심각도·영향: P1. 이력 선택이나 재생성으로 현재 분석 문맥을 예고 없이 잃을 수 있다.
- 근거: [chat-window.tsx](../frontend/src/components/chat/chat-window.tsx), 108행 부근과 [use-agent-chat.ts](../frontend/src/hooks/use-agent-chat.ts), 187행 부근. reset 및 reload prefix 절단. 편집에는 기존 경고가 있음.
- 재현: 사용자 6턴 뒤 다른 이력 선택 → 메시지 0개와 local-current 항목 제거. 중간 답변 재생성도 후속 대화를 제거하는 경로.
- 개선: 현재 비영속 한계와 교체/후속 메시지 제거 영향을 실행 전 안내하고 취소 시 보존한다. 편집·재생성·새 채팅 안내를 일관되게 한다.
- 예상 범위·확신도: 중, 높음(이력 브라우저·재생성 코드). Frontend 안내 독립; 영속 저장·분기 복원은 보류.

### F09 — 실행 상태의 지속적 접근성 알림 부족

- 심각도·영향: P2. 시각적 실행 상태 변화가 보조 기술에 전달되지 않을 수 있다.
- 근거: [thread-messages.tsx](../frontend/src/components/chat/thread-messages.tsx), 90행 부근. 최초 PendingExecution의 status 이후 일반 Tool 그룹에 지속 알림 영역 없음.
- 재현: pending → Tool 실행 → 종료 시 DOM의 status/live 영역 변화 확인.
- 개선: 안정적인 단일 polite 상태 영역에서 의미 있는 단계 전환만 알린다. 토큰·매초 타이머·상호작용 상세 전체를 반복 읽지 않는다.
- 예상 범위·확신도: 소, 중상(DOM 확인; 실제 스크린리더 미검증). Frontend 독립.

### F10 — 경과 시간 부재와 측정 의미 구분 필요

- 심각도·영향: P2. 장기 작업 대기 시간을 판단하기 어렵다.
- 근거: [chat-runtime.ts](../frontend/src/lib/chat-runtime.ts), 183행 부근, [chat.ts](../frontend/src/types/chat.ts), 115행 부근, [use-agent-chat.ts](../frontend/src/hooks/use-agent-chat.ts), 87·109·153행 부근. 현재 lifecycle 측정값이 없음.
- 재현: 긴 요청·Tool 실행·완료·취소 모두 경과 시간 미표시. ID 생성용 Date.now를 측정값으로 사용할 수 없음.
- 개선: 요청 시작→done/error/로컬 취소의 클라이언트 관측 대기 시간을 실제 기록한다. Tool은 동일 호출의 수신→결과 수신 관측값이 있을 때만 표시. 서버 실행 시간으로 부르지 않는다.
- 예상 범위·확신도: 중, 높음(코드). Frontend 독립; 서버 timing은 후속 계약 검토. [공식 timing 문서](https://www.assistant-ui.com/docs/guides/message-timing)와 설치 버전 지원을 확인해 적용.

### F11 — 모션 감소 설정 예외

- 심각도·영향: P2. 모션 감소를 선택한 사용자에게도 회전 애니메이션이 지속된다.
- 근거: [globals.css](../frontend/src/app/globals.css), 88행 부근. reduced-motion 규칙 안에서 execution-activity-spinner 예외.
- 재현: prefers-reduced-motion: reduce 상태에도 계산 스타일 spin 0.6s infinite.
- 개선: reduce일 때 정적 아이콘·텍스트로 상태를 전달하고 기본 환경의 기존 지속 회전 안내는 유지한다.
- 예상 범위·확신도: 소, 높음(브라우저 계산 스타일). Frontend 독립.

### F12 — 빈 응답·0행·누락 결과 구분 부족

- 심각도·영향: P2. 정상적인 0건과 응답 누락을 구별하기 어렵다.
- 근거: [thread-messages.tsx](../frontend/src/components/chat/thread-messages.tsx), 202행 부근과 [database-result.tsx](../frontend/src/components/chat/tool-results/database-result.tsx), 36행 부근. 결과 없는 렌더 경로.
- 재현: done만 수신하면 빈 assistant와 액션; SQL 0행·컬럼/summary 없는 결과에서 본문 null.
- 개선: 빈 assistant, 조회 성공 0건, Tool 결과 미수신, 오류를 구분하고 사실에 맞는 복구 조작을 제공한다.
- 예상 범위·확신도: 소, 높음(브라우저·코드). Frontend 표시, Backend 기존 계약 시나리오 검증.

### F13 — 차트 값의 대체 표현 부족

- 심각도·영향: P2. 차트의 구체적인 값을 시각 그래프 외 방식으로 확인하기 어렵다.
- 근거: [chart-block.tsx](../frontend/src/components/chat/tool-results/chart-block.tsx), 14행 부근. 제목·축·Recharts SVG는 있으나 값의 별도 표/요약 없음.
- 재현: 차트 표시 후 비시각적 값 대안 탐색. SVG role/application·tabindex는 존재하며 “키보드 지원 전무”로 단정하지 않음.
- 개선: 기존 chart.data의 축·단위·값을 재사용하는 접이식 표 또는 동등한 데이터 대안을 제공한다.
- 예상 범위·확신도: 중, 중상(DOM·코드; 실제 스크린리더/tooltip 탐색 미검증). Frontend 독립.

### F14 — Inspector 탭 전환 시 검색 초기화

- 심각도·영향: P2. 반복 탐색에서 필터를 다시 입력해야 한다.
- 근거: [context-inspector.tsx](../frontend/src/components/chat/context-inspector.tsx), 26·32행 부근. 조건부 탭 mount와 로컬 query.
- 재현: 지식 검색 wip → 도구 탭 → 지식 탭에서 검색어 소실.
- 개선: 세션 내 탭별 필터·필요한 스크롤 위치 보존. 기존 탭 역할·roving 키보드 탐색을 유지한다.
- 예상 범위·확신도: 소, 높음(브라우저·코드). Frontend 독립; 서버 저장 불필요.

### F15 — landmark·heading 정보 구조 부족

- 심각도·영향: P2. 주요 작업 영역과 답변 제목의 구조적 탐색이 어렵다.
- 근거: [chat-window.tsx](../frontend/src/components/chat/chat-window.tsx), 149행 부근과 [markdown-text.tsx](../frontend/src/components/assistant-ui/elements/markdown-text.tsx), 31행 부근.
- 재현: main landmark 0개. Markdown h1/h2가 h3로, 하위 제목이 h4로 바뀌어 문서 구조와 의미가 불명확.
- 개선: 레이아웃 landmark·패널 이름·답변 heading 계층을 정의한다. 시각 크기와 의미 수준을 분리하고 큰 장식 제목은 추가하지 않는다.
- 예상 범위·확신도: 소, 높음(DOM·코드; 실제 스크린리더 탐색 미검증). Frontend 독립.

### F16 — SQL 상세의 무제한 높이

- 심각도·영향: P2. 긴 SQL/CTE가 상세 영역을 과도하게 차지한다.
- 근거: [database-result.tsx](../frontend/src/components/chat/tool-results/database-result.tsx), 44행 부근과 [catalog-result.tsx](../frontend/src/components/chat/tool-results/catalog-result.tsx), 115행 부근. 가로 스크롤만 있고 높이 제한 없음.
- 재현: 긴 SQL/CTE 상세를 열면 메시지의 세로 길이가 크게 늘어남.
- 개선: 기존 max-h-96 수준의 제한과 내부 스크롤을 재사용하고 전체 SQL 복사·키보드 접근을 유지한다.
- 예상 범위·확신도: 소, 높음(코드). Frontend 독립; SQL 내용 변경 없음.

### F17 — 준비 중 제어·타입 크기 일관성

- 심각도·영향: P3. 고정된 모델·추론 표시가 실제 설정으로 오인될 수 있고 일부 레이블이 지나치게 작다.
- 근거: [thread.aui.tsx](../frontend/src/components/assistant-ui/elements/thread.aui.tsx), 105행 부근과 [tool-result-card.tsx](../frontend/src/components/chat/tool-result-card.tsx), 142행 부근.
- 재현: disabled GLM-5.3-Flash/Low에 “현재” 의미의 label이 있으나 서버 설정과 연결되지 않음. Details 레이블 10px uppercase가 기존 type scale에서 이탈.
- 개선: 준비 중·고정 예시임을 설명하고 실제 설정처럼 단정하지 않는다. 세부 레이블은 기존 type scale로 통일한다.
- 예상 범위·확신도: 소, 중상(코드; 실제 모델 불일치는 미확인). Frontend 안내 독립; 모델 설정 API는 보류.

## 4. 공유 계약·파트 책임·의존 관계

공유 계약의 기본값은 **변경 없음**이다. 기존 AgentEvent, tool payload,
Result Store, 시각화 명세, SSE·turn/fork 식별자를 유지한다.
이번 문서에서는 신규 payload 필드나 임의의 가상 값을 확정하지 않는다.

| 담당 | 이번 후속 작업 | 선행 조건 |
| --- | --- | --- |
| Frontend | F01~F17 표시·상태·접근성 개선과 회귀 | 최신 코드 재현·기존 계약 확인; 대다수 독립 착수 |
| Backend | F01 표 보완, F02·F12 결과/종료 상관관계 검증·fixture | 기존 mock/fake와 adapter 경로 사용; 새 API 불필요 |
| 공동 | 표 대응 관계와 종료 상태 사례 확인 | F01·F02·F12 최종 인수 전에 fixture와 표시 기대 일치 |
| 후속 검토 | F10 서버 timing, F17 실제 모델, F08 영속 대화 | 별도 범위·계약 합의; 현재 Frontend 수정의 선행 조건 아님 |

기존 계약이 충분하면 Backend 런타임 코드는 변경하지 않는다. 부족한 점이 발견되면
먼저 이 상위 계획의 계약·완료 조건을 합의하고 Backend 스키마와 Frontend 타입·파서를
같은 작업에서 갱신한다. 프론트 관측 시간은 로컬 UI 상태이며 서버 측 실행 시간과 다르다.

## 5. 구현 순서와 전체 인수 조건

1. 결과 정확성·대화 보호: F01·F02·F08, 연관된 Backend fixture 검증.
2. 접근성·반응형: F03~F07, 같은 상세 레이아웃의 F16을 함께 검토.
3. 상태 피드백·시간: F09~F12; 서버 timing 추가 없이 클라이언트 관측값으로 진행.
4. 후속 일관성: F13~F15·F17. P2/P3 세부 우선순위는 파트 계획에서 관리.

아래 조건은 8절의 구현 후 테스트·브라우저 범위에서 충족했다. 실제 보조 기술·운영 환경의 미검증 범위는 별도로 남긴다.

- [x] F01~F17 각각에 최신 재현, 변경 또는 유지 판단, 구현 후 검증 근거가 남는다.
- [x] 별도 결과 표·부분 응답·기존 대화 문맥이 의도치 않게 사라지지 않는다.
- [x] Tool 오류·미완료·0행·빈 응답·취소를 정상 성공과 구별한다.
- [x] 키보드만으로 메시지 조작·상세 열기·패널 전환이 가능하고 숨겨지는 포커스를 복원한다.
- [x] 중요 일반 텍스트 대비, 긴 문자열, landmark·heading, reduced-motion을 검증한다.
- [x] 실측 경계 폭과 400px 수동 패널 개폐에서 입력·전송·닫기 조작을 잃지 않는다.
- [x] 시간은 실제 관측값만 표시하며 단위·측정 범위가 분명하고 알림/렌더 폭주가 없다.
- [x] 관련 Frontend 필수 검증과 브라우저 재현, Backend 변경 시 필수 검증을 새로 수행한다.
- [x] 상태·미검증 영역·보류 결정이 이 문서, 양쪽 실행 계획, Todo에서 일치한다.

### 유지해야 할 기존 동작

- 조회/저장 1,000행·표시 최대 100행, 원본 건수·잘림 안내, 정렬·검색·페이지 크기 선택.
- text/Tool/standalone 표·차트의 의미 있는 문맥 순서와 후속 조회 뒤 기존 결과 보존.
- 공개 실행 안내만 표시하고 비공개 추론·없는 실행 계층·가짜 진행률은 만들지 않음.
- 편집·재생성의 기존 fork 식별자, 취소 후 부분 응답, 오류 복구 시 중복 입력 방지.
- 기본 실행 중 펼침/완료 후 접힘, 일반 환경의 지속 회전 안내와 신규 응답 스크롤 정책.
- Sidebar 전역 전환 시 대화/초안 보존, Inspector 탭 키보드 조작, 지식 관리 미저장 변경 보호.
- SQL 읽기 전용, mock/real 경계, Result Store 접근 범위·TTL, 오류의 내부 정보 미노출.
- 기존 assistant-ui·semantic token·폐쇄망 의존성. 신규 패키지·외부 요청 추가 없음.

## 6. 감사 검증 기록과 한계

2026-09-16의 **감사 시점 기록**이다. 최초 문서 작성에서 다시 실행한 결과가 아니며,
감사 통과를 위 개선 항목의 구현 완료나 구현 후 회귀 통과로 재사용하지 않는다.

- 채팅 브라우저 회귀 **11개 통과**: lifecycle 10개와 실행 표시 1개.
  중복 전송, 최초 오류, 동일 입력 재시도, 빈 종료, 취소 뒤 지연 이벤트,
  취소 후 재입력, 편집·재생성 fork, reset 뒤 지연 이벤트/재입력, 부분 오류와 실행 흐름을 확인했다.
- 지식 관리 브라우저 회귀 **5개 통과**: 초안/노드 유지, 새 채팅·최근 대화 이동,
  스트리밍 중 관리 화면 전환·스크롤, 미저장 변경 유지/폐기, 저장 실패 뒤 편집 내용 보존.
- 제어된 브라우저 응답과 DOM·계산 스타일·코드 검토로 F01~F17을 확인했다.
  기존 회귀 통과는 해당 테스트가 모든 UX 요구를 검증했다는 의미가 아니다.
- assistant-ui 설치 버전 확인 기준: `@assistant-ui/react` 0.15.19,
  `@assistant-ui/react-markdown` 0.14.15. 구현 때 lockfile과 지원 API를 다시 확인한다.
- 실제 LLM/provider·폐쇄망 real 서비스, NVDA/VoiceOver 등 실제 스크린리더,
  모바일 가상 키보드, 수백 턴 대화 성능, 영속 대화 복원·서버 실행 시간은 미검증이다.
- sticky 헤더 포커스 가림과 동시 실행 Tool의 조기 완료는 추가 확인에서 결함으로
  확정되지 않았으므로 새 감사 항목으로 등록하지 않았다.

## 7. 결정·문서화 기록

- 2026-09-16: 상위 계획과 양쪽 실행 계획으로 분리. 감사 ID는 유지하고 개선 구현은 미착수.
- 최초 문서화는 계획 문서 4개로 한정했고 기존 완료 계획과 사용자의 미커밋 변경을 유지했다.
- 문서 검증 완료: 변경 문서 4개의 상대 링크 96개, 신규 파일명 3개,
  상위 F01~F17 각 1회 등록·Frontend 주 책임 각 1회 배분, 양쪽 상태 일치와
  구현 완료 체크 없음 확인. `git diff --check` 통과, 신규 문서 3개도
  `git diff --no-index --check /dev/null <파일>`로 공백 경고 없음을 확인했다.
- 애플리케이션 테스트·build·lint는 이번 문서화 작업에서 다시 실행하지 않았다.

## 8. 구현·검증 기록 — 2026-09-16

FE-01~06과 BE-01~03 완료. 신규 패키지·API·SSE 필드는 추가하지 않았다.
Backend는 기존 계약으로 요구 상태를 표현할 수 있어 런타임 변경 없이 테스트만 추가했다.

- F01: 검증된 standalone payload와 컬럼·전체 행이 일치하는 단순 Markdown 표만 중복 처리한다.
  별도 지표·불명확한 서식·코드 펜스는 보존한다.
- F02·F12: 오류·미완료를 접힌 그룹에도 집계하고 빈 응답, 조회 0건, 누락 결과를 구분한다.
- F03·F05~F09·F11: 액션 DOM 유지, 핵심 메타 ink-2, 긴 본문 wrapping,
  자동 접힘 포커스 복원, 대화 교체/재생성 전 확인, 단일 상태 알림, reduce 시 정적 아이콘을 적용했다.
- F04·F16: 기존 임계값 아래에서 재개방한 패널은 Chat을 압축하지 않는 비모달 overlay다.
  Escape·Tab 이탈·닫기 동작과 포커스 복귀를 제공하며 SQL/CTE는 max-h-96 내부 스크롤을 쓴다.
- F10: performance.now 기반 요청/Tool 관측값을 프론트 로컬 상태에만 기록한다.
  측정값 없는 과거 데이터에는 표시하지 않고, 서버 시간으로 표현하지 않는다.
- F13~F15·F17: 차트 값의 접이식 표, Inspector 탭 상태 보존, main/이름 있는 aside와
  답변 h2 아래 h3~h6 제목, 실제 설정 미연결 표시와 기존 type scale을 적용했다.
- 상세 결정과 변경 파일·시험 대응은 [Frontend 9절](../frontend/plan/260916-agent-workbench-ux-audit-plan.md),
  [Backend 8절](../backend/plan/260916-agent-workbench-ux-audit-plan.md)에 기록했다.

### 새로 실행한 검증

| 검증 | 구현 후 결과 |
| --- | --- |
| Frontend npm test | 66개 통과 |
| Frontend npm run build | 성공; 기존 500kB 이상 chunk 경고 유지 |
| Frontend npm run lint | 오류 0, 기존 Fast Refresh 경고 13개 |
| Backend python -m pytest -q | 259개 통과, 6개 deselected |
| 기존 채팅 브라우저 | lifecycle 10 + 실행 표시 1 = 11개 새로 통과 |
| 기존 지식 관리 브라우저 | 5개 새로 통과 |
| 신규 Workbench 브라우저 | 1440px 일반 모션 9개, 400px reduced-motion 9개 통과 |
| 키보드 수동 재현 | 이전 질문 복사 → Tab → 편집; 400px Inspector에서 Shift+Tab → Composer와 패널 닫힘 |

브라우저는 실제 App과 결정적 fetch/SSE fixture를 사용했다. 실제 provider를 호출하거나
운영 데이터를 변경하지 않았다. 기존 감사 통과 기록을 새 검증으로 재사용하지 않았다.

### 구현 후 폭 실측

1440 → 1180 → 1179 → 860 → 859 → 768 → 400px로 축소한 기본 pane 폭은
2절의 기본 상태와 동일하다. 역순 확대 시 패널은 자동으로 펼쳐지지 않고 수동 선택을 유지한다.
모든 경계에서 페이지 가로 overflow가 없었다.
400px에서 Inspector 재개방 시 Inspector 320px(x=80), **Chat 400px, 입력창 334px**으로
감사 당시 Chat 80px/입력창 14px 문제를 해소했다. 1440px 기본 입력창은 726px이다.

### 남은 검증·보류

실제 LLM/provider·폐쇄망 real 서비스, NVDA/VoiceOver 낭독, 모바일 가상 키보드,
수백 턴 성능은 이번 환경에서 검증하지 않았다. 접근성 통과는 DOM·계산 스타일·
브라우저 키보드 검증 범위이며 WCAG 전체 적합성 인증을 뜻하지 않는다.
서버 timing·실제 모델 설정 조회·대화 영속 저장/분기 복원은 BE-04~05로 계속 보류한다.

문서 검증: 계획/Todo/디자인 문서의 상대 링크 129개, 감사 ID 17개와 Frontend 배분
17개 누락·중복 없음, 상위·파트 상태 일치, 보류 체크박스 미완료를 확인했다.
`git diff --check` 및 신규 파일 11개의 공백 검사도 경고 없이 통과했다.

## 9. 후속 정책: 화면 전환 확인창 제거

2026-09-16 사용자 요청. F08의 기존 구현 기록은 보존하되 새 채팅·예시 세션
선택에는 비영속 경고 확인창을 띄우지 않는 정책으로 대체한다. 초기화 동작·
지식 편집 미저장 보호·답변 재생성 확인은 유지한다. 세션 DB 저장과 공유 API 변경은
이번 범위가 아니다. Frontend 단독 변경이며 Backend 작업은 없다.

- 상태: 구현·검증 완료.
- 인수 조건: 대화/초안이 있어도 새 채팅·다른 예시 세션으로 확인창 없이 전환된다.
  관리 화면 왕복·미저장 편집 보호·재생성 취소 회귀는 유지한다.
- 실행 기록: [Frontend 후속 단계](../frontend/plan/260916-agent-workbench-ux-audit-plan.md#10-후속-정책-화면-전환-확인창-제거).
- 새 검증: Frontend 테스트 66개, Workbench 브라우저 9개, 지식 관리 브라우저 5개 통과.
  build 성공, lint 오류 0(기존 경고 13개), 기존 대형 bundle 경고 유지.

## 10. 후속 기능: Context Inspector 너비 조절

2026-09-16 사용자 요청. Frontend 레이아웃만 변경하며 Backend·assistant-ui
런타임·SSE 계약은 바꾸지 않는다.

- 상태: 구현 완료. 실제 브라우저 수동 검증은 브라우저 제어 환경 부재로 보류.
- 기본 폭: 20rem, viewport 1280px 이상은 23rem. 세션 내 사용자 지정 폭은
  16~35rem이며 중앙 Chat 최소 32.5rem과 viewport를 우선해 상한을 제한한다.
- 조작: Inspector 좌측 경계 포인터 드래그, 키보드 `←/→`, `Home/End`,
  더블클릭 기본 폭 복원을 제공한다. separator role과 현재/최소/최대 폭을 노출한다.
- 반응형: 1180px 미만의 기존 비모달 overlay와 자동 접힘·포커스 복귀를 유지하고,
  overlay 폭은 viewport에서 3rem 여백을 남기는 범위로 제한한다.
- 검증: Frontend 테스트 67개 통과, build 성공, lint 오류 0·기존 경고 13개,
  `git diff --check` 대상. Workbench 브라우저 회귀에 키보드 폭 변경 fixture를 추가했다.
- 실행 기록: [Frontend 후속 단계](../frontend/plan/260916-agent-workbench-ux-audit-plan.md#11-후속-기능-context-inspector-너비-조절).
