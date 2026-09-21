# Production Planning Agent Frontend 계획 및 이력

**상태: 진행 중. 마지막 갱신: 2026-09-21.**

이 문서는 Frontend 작업의 목표, 기대 API 계약, 다음 작업과 완료 이력을 관리하는
단일 기준 문서다. 폐쇄망 반입 후 Frontend workspace만 열어도 이해할 수 있도록
다른 workspace의 계획 문서를 전제로 하거나 링크하지 않는다.

## 목표와 책임

Vite·React·assistant-ui 기반 3-pane Agent Workbench에서 생산계획 Agent의
streaming 답변, 공개 실행 단계, Tool 결과, 표·차트와 지식 관리를 정확하고
접근 가능하게 제공한다.

Frontend가 소유하는 범위는 다음과 같다.

- 브라우저 SSE transport와 메시지·retry·cancel·edit·regenerate 상태
- assistant-ui External Store runtime과 Thread·Composer·메시지 렌더링
- Tool 실행 과정, 독립 표·차트와 안전한 payload parser
- Sidebar, Knowledge Manager, Context Inspector와 반응형 3-pane layout
- 접근성, focus·keyboard·reduced-motion, loading·empty·error 상태
- 폐쇄망 build·asset·환경 설정과 브라우저 회귀 검증

브라우저의 LLM 직접 호출, Cloud persistence, 원격 asset/CDN, 모바일 전용 UX와
Backend에 없는 기능을 동작하는 것처럼 표시하는 것은 범위 밖이다.

## 현재 구현 상태

| 영역 | 상태 | 현재 기준 |
| --- | --- | --- |
| 채팅 runtime | 완료 | assistant-ui External Store, SSE, retry·cancel·edit·regenerate |
| 메시지 lifecycle | 완료 | complete/cancelled/error, 부분 응답과 terminal event 구분 |
| 실행 과정 | 완료 | 공개 status, ToolGroup, 호출 ID별 args/result와 2단계 disclosure |
| 표 | 완료 | 최대 100행, 검색·정렬·10/25/50/100 pagination, 문맥 순서 보존 |
| 차트 | 완료 | 검증 API 기반 bar/line, loading/error와 데이터 표 대안 |
| 지식 관리 | 완료 | 구조화 지식 조회, 텍스트 등록·검토·활성화, 정확한 버전 인용 |
| Layout | 완료 | Sidebar·Chat·Inspector, Inspector resize, 좁은 화면 overlay |
| 접근성 감사 | 범위 내 완료 | keyboard/focus/label/landmark/reduced-motion/긴 문자열/0행·빈 응답 |
| 세션 목록 | 예시 상태 | 현재 실행 동안만 유지; 영속 저장은 미구현 |
| 실행 환경 | 완료 | Frontend 기본 포트 3100, API 기본 주소 8100 |

## Backend에 기대하는 안정 계약

Frontend는 상대 workspace 문서를 읽지 않고 아래 입력 계약만 전제로 한다. 계약이
달라지면 이 문서를 먼저 갱신하고 parser·fixture·UI를 같은 작업에서 변경한다.

### AgentEvent와 메시지

- event type: `text`, `status`, `tool_call`, `tool_result`, `error`, `done`.
- `tool_call_id`는 같은 호출의 args와 결과를 연결한다.
- 성공한 `done.data.turn_id`는 편집·재생성의 `fork_from_turn_id`로 사용한다.
- 오류 흐름은 `error` 다음 terminal `done`으로 끝난다.
- 서버 thinking이나 비공개 추론은 전달·표시하지 않는다.
- 현재 `done`에는 동적 후속질문이 없다. 도입 시 선택 배열 필드를 엄격히 검증한다.

### 표·차트·지식

- `prepare_table` 성공 결과는 columns, rows, row_count, displayed_count와
  source_truncated를 포함하며 rows는 최대 100행이다.
- `prepare_visualization` 성공 결과의 `visualization_id`로
  `/api/visualizations/{id}`를 조회한다.
- 지식 API는 Tool·Skill·구조화 entry와 버전형 text document를 제공한다.
- 문서 검색 Tool 이름은 `search_documents`이며 결과 `kind`는 `knowledge`다.
- 브라우저는 credential cookie를 포함하고 내부 path·scope를 표시하지 않는다.
- malformed·oversized·알 수 없는 payload는 안전한 오류 UI로 전환한다.

## 다음 작업

### P1

- [ ] **후속질문 동적 생성 UI**: 성공한 assistant 응답의 2~4개 제안을 thread
  suggestions로 표시하고 클릭 시 전송한다. 오류·취소·과거 메시지·빈 배열에서는
  표시하지 않으며 고정 welcome 예시는 유지한다.

### P2

- [ ] 실제 screen reader, 모바일 가상 키보드와 긴 대화 성능을 운영 환경에서
  검증한다.
- [ ] Fast Refresh lint warning과 production bundle 크기 경고를 기능 변경과
  분리해 정리한다.
- [ ] 실제 모델 설정 API가 제공될 때 현재 비활성 모델·추론 강도 control의 표시
  정책을 재검토한다. API가 없으면 비활성 안내를 유지한다.
- [ ] 결과 필터·재집계 API가 제공될 때 Result Store 후속 탐색 UX를 별도 계획한다.

### P3

- [ ] 영속 대화·분기 API와 인증 principal이 제공될 때 현재 예시 ThreadList를 실제
  저장소로 전환한다.
- [ ] 실제 사내 서비스 환경에서 SQL·RAG·simulation 오류, 장시간 streaming과
  재연결을 관통 검증한다.

## 완료 이력 요약

### 2026-09-08~14 — 기본 Workbench와 지식 조회

- SSE 채팅, 3-pane Workbench, Tool 결과 카드와 편집·재생성·취소·복사를
  구현했다.
- 구조화 지식·Skill 조회와 Context Inspector를 연결했다.
- 구조화 지식 상세 응답에서 simulation도 선택 필드 `aggregation_rules`, `visualization_hints`를
  가질 수 있다. 기존 상세 렌더러가 필드 이름별 라벨("집계 규칙", "시각화 안내")로 표시한다.

### 2026-09-15 — assistant-ui 안정화와 결과·차트

- External Store 상태 소유권을 정리하고 deprecated iteration과 과장된 capability를
  제거했다.
- streaming parser, terminal lifecycle, retry race와 오류 payload 표시를
  회귀 테스트로 고정했다.
- Result Store 대용량 요약과 검증된 bar/line 차트, loading·retry·fallback을
  구현했다.
- SMT2020 기반 예시 질문·정적 콘텐츠와 관통 흐름 검증을 정리했다.

### 2026-09-16~18 — Elements, Tool UI와 UX 감사

- assistant-ui Elements 기반 Thread·Composer·ToolCall·AgentPlan·ThreadList로
  공통 UI를 전환했다.
- delta 답변, ToolGroup, 공개 진행 안내와 호출 ID별 args/result 표시를 구현했다.
- standalone 표·차트와 TanStack Table을 적용하고 `도입 → 결과 → 해석`의 원래
  이벤트 문맥 순서를 보존했다.
- Sidebar 내비게이션, 지식 관리, Inspector resize와 스크롤 안정화를 구현했다.
- F01~F17 감사에서 표 소실, 성공 오인, hover-only action, 좁은 화면 panel,
  focus 복원, 대비·긴 문자열, 0행·빈 응답, 실제 client timing, reduced-motion과
  landmark를 개선했다.

### 2026-09-21 — 실행·계획 기준 정리

- Vite dev/preview 포트를 3100, 기본 Backend 주소를 8100으로 통일했다.
- 상세 날짜형 계획을 이 문서로 통합하고 Frontend workspace 독립 계획 체계로
  전환했다.

## 유지할 UI 결정

- Chat이 primary이며 Sidebar 15.5rem, Inspector 기본 20rem(1280px 이상 23rem),
  Thread 읽기 폭 47.5rem을 기준으로 한다.
- Inspector는 16~35rem에서 조절하며 Chat 최소 폭을 보호한다. 1180px 아래에서
  Inspector, 860px 아래에서 Sidebar를 임계값 하향 통과 시 한 번만 접는다.
- pane은 마운트를 유지하고 좁은 화면 재개방은 Chat을 밀지 않는 overlay다.
- 일반 UI는 semantic CSS token과 light theme만 사용한다. 외부 font·CDN과 새
  remote runtime을 추가하지 않는다.
- Tool 실행은 최종 답변보다 낮은 위계로 두고 완료 후 자동으로 접는다.
- 표·코드에는 가로·세로 scroll cap을 적용하고 숫자·식별자는 mono와
  tabular-nums를 사용한다.
- 미연결 기능은 비활성화하고 이유를 표시한다. 실제 계약 없이 값을 추측하지 않는다.

## 검증 기준과 알려진 한계

- 필수 검증: `npm test && npm run build && npm run lint`.
- 2026-09-21 통합 직전 기준: **67 tests passed**, build 성공, lint 오류 0개와
  기존 Fast Refresh warning 13개. production bundle 크기 경고는 남아 있다.
- 브라우저 회귀는 chat, knowledge, workbench 전용 harness에서 lifecycle·focus·
  resize·좁은 화면을 확인한다.
- 실제 screen reader, 모바일 키보드, 실제 provider 장시간 응답과 영속 세션은
  아직 검증하지 않았다.

## 계획 운영

- 작은 작업은 이 문서의 다음 작업·상태·완료 이력을 직접 갱신한다.
- 큰 작업만 같은 폴더에 `<yymmdd>-<topic>-plan.md`를 만들며 Frontend 목표·기대
  API·UI 상태·Task·검증을 문서 안에 완결한다.
- 다른 workspace 계획을 링크하거나 구현 상태를 추정하지 않는다. 필요한 외부
  계약은 요청·응답·오류·착수 조건으로 이 문서 또는 활성 계획에 직접 기록한다.
- 작업 완료 후 장기적으로 필요한 결정과 검증만 이 문서에 합치고 상세 실행 계획은
  제거해 이 폴더를 간결하게 유지한다.
