# Frontend UI/UX 개선 실행 계획 (frontend-design Skill)

- 상태: 완료
- 상위 계획: [../../plan/260916-frontend-ui-ux-plan.md](../../plan/260916-frontend-ui-ux-plan.md)
- 필요한 백엔드 계획: 없음(공유 계약 미변경)
- 착수 조건: 없음(단독 프론트엔드 작업)

## 1. 사용한 Skill과 적용 판단

`frontend-design` Skill(설치됨)을 명시적으로 호출했다. 이 Skill은 범용
챗봇이 아니라 "업무용 밀도 높은 Agent Workspace"라는 이 제품의 성격에 맞게
다음과 같이 판단을 조정해 적용했다.

- Skill이 경고하는 "생성형 AI 디자인의 흔한 tell"(크림 배경+세리프+테라코타
  액센트, 카드화, 그라디언트, ALL CAPS 라벨 등)은 애초에 기존 디자인에
  없었다 — 기존 토큰(무채색 표면 3단계 + 액센트 1개 + 저채도 상태 3색,
  1px 룰 기반 구분)이 이미 이 원칙과 일치했으므로 색·타이포 체계를
  다시 만들지 않고 유지했다.
- Skill의 "하나의 대담한 요소에 집중하고 나머지는 절제" 원칙은 색상이
  아니라 **정보 위계**(무엇이 펼쳐져 있고 무엇이 접혀 있는가)에 적용했다 —
  이 제품에서 가장 중요한 판단은 팔레트가 아니라 "완료된 Tool 실행 결과를
  기본으로 펼칠 것인가"였다.
- "숫자 마커(01/02/03)는 실제 순서가 있을 때만" 원칙은 이미 지켜지고
  있었다(Tool 단계는 실제 순서가 있는 실행 로그이므로 유지).
- 새로운 시각적 정체성을 만들기보다, 기존 토큰 체계 안에서 실제 사용 시
  드러나는 결함(펼침 상태, 미연결 affordance, 리사이즈 충돌)을 고치는 데
  Skill의 "절제·정직함·정보 위계" 원칙을 활용했다.

## 2. 실제 코드 기준 UI/UX 분석 요약

### P0 — 오해를 유발하는 미연결 affordance

1. `context-inspector.tsx` Prompt 탭의 "저장" 버튼이 `onClick` 자체가 없어
   눌러도 아무 일도 일어나지 않았다(비활성 상태만 `dirty` 로컬 값으로
   흉내). 편집 textarea도 새로고침·탭 전환 시 사라지는데 사용자에게
   그 사실이 전혀 드러나지 않았다.
2. `app-sidebar.tsx`의 설정(톱니바퀴) 버튼에 `onClick`이 아예 없었다 —
   호버 스타일만 있어 클릭 가능한 것처럼 보였다.
3. Sidebar 세션 목록이 구체적인 제목·상대 시각·도구 흔적 아이콘을 보여줘
   실제 저장된 이력처럼 보이지만, 시드 세션 외에는 선택 시 완전히 빈
   대화가 열린다. 목록 위에 이것이 예시라는 표시가 전혀 없었다.

### P1 — 진행 상태 이해·가독성

4. `tool-result-card.tsx`가 `defaultOpen={kind !== "catalog"}`로 database/
   simulation/knowledge/generic 결과를 **항상** 펼친 채로 렌더링했다. 시드
   대화만 해도 SQL 10행 표 + 시뮬레이션 11행 표가 완전히 펼쳐진 채 최종
   답변 위에 쌓여, 실제로 중요한 최종 답변이 스크롤 없이는 보이지 않았다.
   "완료 후에는 실행 이력이 최종 답변보다 낮은 위계를 가져야 한다"는 목표와
   정면으로 어긋났다.
5. 접힌 카드 헤더의 한 줄 요약(`catalogSummary`)이 catalog 종류에만
   있었다 — #4를 고쳐 기본 접힘으로 바꾸면 database/simulation/knowledge
   카드는 접힌 채 아무 단서도 없는 상태가 된다.
6. `DataTable`/Markdown `Table`에 가로 스크롤은 있었지만 세로 높이 제한이
   없어, 100행에 가까운(large_result 임계값 미만) inline 표가 화면 전체를
   세로로 덮을 수 있었다.
7. `chat-window.tsx`의 반응형 collapse `useEffect`가 매 `resize` 이벤트마다
   무조건 임계값 아래인지 검사해 패널을 닫았다 — 사용자가 좁은 화면에서
   직접 pane을 펼친 뒤 창을 드래그(resize가 초당 수십 번 발생)하면 그
   조작을 계속 되돌렸다.
8. Composer의 `ComposerPrimitive.Input`에 접근성 이름이 placeholder에만
   의존했다.

### P2

- 나머지(상태 아이콘+텍스트 병기, 포커스 링, 키보드 전송, 카탈로그 기본
  접힘, 진행 블록 open/touched 패턴 등)는 이미 이 프로젝트가 잘 지키고
  있어 변경하지 않았다. 특히 `AgentProgress`의 "실행 중엔 자동 펼침,
  사용자가 건드리면 그 상태 유지" 패턴은 이미 있던 설계였고, 이번 작업은
  Tool 결과 카드에도 **같은 패턴을 확장**한 것이다.

## 3. Task와 실제 변경

### Task 1 — Tool 결과 카드 progressive disclosure

- 대상: `src/components/chat/tool-result-card.tsx`,
  `src/components/chat/thread-messages.tsx`
- 변경:
  - `ToolResultCard`에 `isRunning`(그 결과를 담은 assistant 메시지의 실행
    여부) prop을 추가했다. catalog는 항상 기본 접힘, 그 외는
    `autoOpen = isRunning`으로 실행 중엔 펼치고 완료되면 접는다.
    `AgentProgress`와 동일한 `open`/`touched` 패턴으로 사용자가 수동
    토글하면 그 상태를 유지한다.
  - `ai-elements/tool.tsx`의 `Tool`(`Collapsible` 래퍼)은 이미
    `open`/`onOpenChange`를 지원해(`@base-ui/react/collapsible`) 별도
    수정 없이 controlled 모드로 전환했다.
  - `resultHeaderSummary()`를 추가해 catalog 외 종류도 접힌 헤더에서
    핵심을 보여준다: database → `N행`, simulation → `지표 N개`(없으면
    `N건`), knowledge → `문서 N건`.
  - `thread-messages.tsx`의 `AssistantMessage`가 이미 갖고 있던
    `isRunning`(`useAuiState`)을 `ToolPart`/`ToolResultCard`로 전달한다.
- 회귀 위험 점검: 메시지가 나중에 running→complete로 바뀔 때 같은 컴포넌트
  인스턴스가 유지되며 `useEffect`가 `isRunning` 변화를 반영해야 한다 —
  `AgentProgress`가 이미 검증된 패턴이라 동일하게 동작함을 브라우저에서
  확인(§5).

### Task 2 — 큰 inline 표의 세로 높이 제한

- 대상: `src/components/chat/primitives.tsx`(`DataTable`),
  `src/components/chat/markdown-text.tsx`(`Table`)
- 변경: 두 표 래퍼 모두 `thin-scroll max-h-96 overflow-x-auto overflow-y-auto`
  로 통일. 가로 스크롤 동작은 그대로, 세로는 24rem(384px) 안에서만
  스크롤한다.

### Task 3 — 반응형 collapse의 resize 충돌 수정

- 대상: `src/components/chat/chat-window.tsx`
- 변경: `prevWidthRef`로 이전 폭을 추적해 **임계값을 아래로 통과하는
  순간에만** `setSidebarOpen(false)`/`setInspectorOpen(false)`를 호출한다.
  이미 임계값 아래인 채로 발생하는 추가 resize 이벤트는 무시한다.

### Task 4 — 오해를 유발하는 미연결 affordance 정리

- 대상: `src/components/chat/context-inspector.tsx`,
  `src/components/chat/app-sidebar.tsx`
- 변경:
  - Prompt 탭: 편집 textarea + "저장"/"되돌리기" 버튼을 제거하고 읽기
    전용 `<pre>`로 바꿨다. 캡션에 "읽기 전용 · 저장 기능 미연결"을 명시.
  - Metadata 탭: 패널 첫 줄에 "현재 세션 실행 정보 예시 · 아직 실제 연결
    값이 아닙니다" 캡션 추가.
  - Sidebar: 설정 버튼을 `disabled` + `aria-label="설정 (준비 중)"` +
    `title`로 바꿔 눌러도 반응이 없는 이유를 밝혔다. 세션 목록 위에
    "예시 세션 · 현재 대화만 유지됩니다" 캡션을 추가했다.
  - 세션 선택 시 시드 외에는 빈 대화가 열리는 기존 동작 자체는 바꾸지
    않았다(영속 저장소를 새로 만들지 않는다는 비범위 유지).

### Task 5 — Composer 접근성

- 대상: `src/components/chat/message-input.tsx`
- 변경: `ComposerPrimitive.Input`에 `aria-label="메시지 입력"` 추가.

### Task 6 — 디자인 가이드·계획 문서 반영

- 대상: `frontend/CLAUDE.md`(신규 디자인 가이드 섹션),
  `plan/260916-frontend-ui-ux-plan.md`(신규),
  `frontend/plan/260916-frontend-ui-ux-plan.md`(이 문서), `plan/Todo.md`.

## 4. 검증

### 정적 검증

```bash
cd frontend
npm test       # 27 pass (기준선과 동일, 회귀 없음)
npm run build  # tsc -b && vite build 성공, 500kB 청크 경고는 기존과 동일(무관)
npm run lint   # 0 errors / 3 warnings — 기존 3건(button.tsx/sidebar.tsx/tabs.tsx의
               # react-refresh/only-export-components)과 동일, 새 경고 없음
```

기준선(수정 전)도 동일 명령으로 확인: test 27 pass, build 성공(동일 경고),
lint 0 errors/3 warnings. 이번 작업으로 인한 새 실패·경고 없음.

### 브라우저 검증 (Playwright, `npm run dev` 대상 `localhost:3000`)

- 데스크톱(1440×900): 시드 대화의 Tool 결과 카드 2개(execute_sql 10행,
  run_simulation 지표 4개)가 완료 상태에서 접혀 있고, 헤더에 "데이터 조회 ·
  10행", "시뮬레이션 실행 · 지표 4개"가 보이며 최종 답변이 스크롤 없이
  바로 아래 보임을 확인.
- Prompt 탭: 읽기 전용 캡션·본문, 저장 버튼 없음을 확인.
- Metadata 탭: 예시 데이터 캡션 확인.
- Sidebar: "예시 세션…" 캡션, 설정 버튼 `disabled` 상태(접근성 트리에서
  `[disabled]`, 이름 "설정 (준비 중)") 확인.
- 400×800: `document.documentElement.scrollWidth === clientWidth`(가로
  스크롤 없음) 확인. Composer 입력·전송 버튼이 겹치거나 잘리지 않음을
  스크린샷으로 확인.
- 900×800(Sidebar 열림/Inspector 접힘 구간)에서 Inspector를 수동으로 편 뒤
  905→895→910px로 연속 resize해도 Inspector가 다시 닫히지 않음을 확인
  (Task 3 회귀 재현 시나리오).
- 새 대화(빈 대화) 상태, 예시 질문 클릭 → 백엔드 미기동으로 인한
  `ConnectionBanner`(요청 주소·점검 목록·재시도 버튼)와 사용자 메시지
  보존·편집 affordance 확인.
- `/tests/chat-browser.html`: 10개 시나리오(중복 전송 방지, 백엔드 오류,
  재시도, 무출력 연결 실패, 취소 후 새 요청, 동시 틱 취소+전송, 재생성/편집
  fork anchor, reset, partial error) 모두 `PASS`.
- 브라우저 콘솔 오류: Skills API 호출 실패(`ERR_CONNECTION_REFUSED`,
  백엔드 미기동) 외 새 오류 없음 — 이 오류는 기존 동작(`SkillsPanel`의
  `failed` 상태)이 의도한 대로 처리한다.

### 확인하지 못한 항목과 사유

- **실시간 SSE 스트리밍 중 상태**(Tool 카드가 실행 중 자동으로 펼쳐지는
  순간, 진행 블록이 단계별로 갱신되는 순간)는 실제 백엔드나
  `PLANNING_AGENT_FAKE=1` Fake Runner를 이 세션에서 기동하지 못해(Python
  가상환경 미구성, 백엔드 의존성 미설치) 육안으로 직접 보지 못했다. 대신
  다음 두 근거로 대체 검증했다: (1) 동일한 `open`/`touched`/`isRunning`
  패턴을 쓰는 `AgentProgress`가 이미 이 제품에서 실행 중 자동 펼침·완료 후
  접힘으로 정상 동작하고 있고, `ToolResultCard`는 그 패턴을 그대로
  재사용한다. (2) `/tests/chat-browser.html`이 텍스트/툴/에러 혼합 스트림,
  부분 실패, 취소를 실제 `ReadableStream`으로 재현해 상태 전이 로직 자체는
  검증했다. 완전한 신뢰도를 위해서는 백엔드를 기동한 수동 확인이 남아있다.
- Sheet/overlay 기반 좁은 화면 레이아웃(§6에서 언급된 대안)은 구현하지
  않았다 — 아래 "제외한 부분" 참고.

## 5. 이번 작업에서 제외한 부분

- **좁은 화면 전용 Sheet/overlay 패널**: 현재는 임계값 아래에서 패널이
  폭 0으로 접히고, 다시 펴면 Chat 컬럼을 인라인으로 밀어낸다. `ui/sheet.tsx`
  가 이미 설치돼 있어 오버레이 방식으로 바꿀 수 있지만, 포커스 트랩·진입/
  퇴장 모션·기존 collapse 상태 관리와의 상호작용까지 새로 설계해야 해서
  이번 작업 범위(기존 상태 소유권 보존, 과도한 변경 지양)에서는 제외했다.
  현재 방식도 400px까지 가로 스크롤 없이 동작하는 것은 확인했다.
- **Sidebar 세션 선택 시 빈 대화가 열리는 동작 자체**: 캡션으로 명확히
  했을 뿐 실제 persistence는 만들지 않았다(비범위 유지, §8 지침).
- **표 헤더 sticky 처리**: `max-h-96` 스크롤 캡을 추가하면서 헤더가 함께
  스크롤되어 올라간다. sticky 헤더는 배경색이 카드마다 달라(캔버스/서페이스
  2/투명) 얼룩 없이 고정하려면 별도 배경 규칙이 필요해 이번 범위에서는
  제외했다.
- **Metadata/시뮬레이션 서버 상태의 더 근본적인 처리**(탭 자체를 감추거나
  하위로 이동): 캡션으로 명확히 하는 방식을 선택했다(§8의 선택지 중 (a)).
  실제 연결 계약이 생기면 재검토한다.

## 6. 변경 파일 목록

- `frontend/src/components/chat/tool-result-card.tsx`
- `frontend/src/components/chat/thread-messages.tsx`
- `frontend/src/components/chat/primitives.tsx`
- `frontend/src/components/chat/markdown-text.tsx`
- `frontend/src/components/chat/chat-window.tsx`
- `frontend/src/components/chat/context-inspector.tsx`
- `frontend/src/components/chat/app-sidebar.tsx`
- `frontend/src/components/chat/message-input.tsx`
- `frontend/CLAUDE.md`(신규 디자인 가이드 섹션)
- `plan/260916-frontend-ui-ux-plan.md`(신규)
- `frontend/plan/260916-frontend-ui-ux-plan.md`(이 문서, 신규)
- `plan/Todo.md`(상태 갱신)
