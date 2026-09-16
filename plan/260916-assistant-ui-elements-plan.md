# assistant-ui Elements 전환

- 상태: 완료
- 마지막 갱신: 2026-09-16
- 기준: [Todo](Todo.md)
- 실행: [Frontend 실행 계획](../frontend/plan/260916-assistant-ui-elements-plan.md)

## 목표와 범위

공식 assistant-ui Base 템플릿과 Elements를 바탕으로 Thread, Composer, 메시지
액션, 세션 목록, 진행 단계, 도구 결과 disclosure를 재구성한다. 복사 소스는
저장소에서 관리하고 한국어·기존 semantic token·접근성에 맞게 조정한다.
생산계획 전용 Inspector, SQL/Result Store/차트 renderer는 확장 슬롯으로 유지한다.

## 공유 계약과 결정

- FastAPI AgentEvent SSE, turn_id/fork_from_turn_id, Result Store와 시각화 계약은
  변경하지 않는다. useAgentChat와 useExternalStoreRuntime이 상태를 계속 소유한다.
- 요청된 useChatRuntime 안내는 프론트 AGENTS.md에 추가하되, 현재 SSE에는
  AI SDK transport를 사용할 수 없다는 프로젝트 적용 예외를 바로 명시한다.
- AssistantRuntimeProvider는 App 루트, Thread는 전체 채팅에 사용한다.
  AssistantModal은 향후 floating widget에 적용하는 패턴으로만 기록한다.
- 기존 AI Elements 사용 결정은 assistant-ui Elements 우선으로 대체한다.
- 실제 세션 저장 계약이 없으므로 props 기반 ThreadList를 사용한다.
  Cloud, 음성, 첨부, 모델 선택, 공유·삭제와 가짜 동작은 추가하지 않는다.
- 3-pane, 읽기 폭, 최종 답변 우선순위와 수동 펼침 유지 규칙을 보존한다.
- 새 npm 의존성과 외부 런타임 통신은 추가하지 않는다.

## 할당과 의존 관계

Frontend 단독 작업이다. Backend 구현·계획 변경은 필요하지 않다.
공식 MCP 문서와 registry 소스를 검토한 후 설치된 패키지 타입으로 검증한다.
기존 완료 계획은 과거 이력으로 보존하고 새 결정에서 대체 범위를 명시한다.

## 인수 조건

- [x] 공식 Elements 기반 공통 UI와 생산계획 확장 코드가 분리된다.
- [x] AI Elements 의존이 제거되고 요청한 지침 및 충돌 설명이 반영된다.
- [x] 전송·중단·재시도·편집·재생성, 도구/진행 펼침, 차트/표가 유지된다.
- [x] npm test/build/lint와 브라우저 lifecycle 및 실제 UI 검증을 통과한다.
- [x] 외부 asset·런타임 요청 없이 desktop/좁은 화면이 동작한다.


## 후속 CLI 설치 (2026-09-16, 완료)

사용자 지정 shadcn 명령으로 Thread/ThreadList의 공식 관련 소스 12개를 추가했다.
기존 커스텀 Thread와 도메인 확장은 덮어쓰지 않았다. 이 후속 요청에서
신규 의존성 제한은 CLI 필요 범위로 변경했다: tw-shimmer 0.4.13 추가 및 기존
zustand 5.0.15의 직접 의존성 선언. 런타임 세션 adapter와 backend 변경은 없다.
검증 결과와 세부 적용은 [Frontend 실행 계획](../frontend/plan/260916-assistant-ui-elements-plan.md)의
후속 기록을 따른다.


## 후속: Elements 카탈로그 추가 적용 (2026-09-16, 완료)

- 공식 messages 및 관련 카탈로그와 MCP 문서를 검토한다.
- ErrorState: 연결 실패와 메시지 오류에 실제 재시도 액션을 연결한다.
- EditMessage: 현재 메시지 이후 사라지는 답변 수를 알리고 runtime 편집을 유지한다.
- StoppedRun: 중단 상태와 같은 질문 다시 실행을 연결한다. 이어쓰기로 표시하지 않는다.
- RetrievalChunks: 실제 검색 문서·출처·스니펫과 제공된 유효 관련도만 표시한다.
- PromptLibrary: 기존 예시 질문 검색·미리보기·키보드 선택 후 draft 끝에 삽입한다.
- Backend/SSE·저장·시각화 계약은 유지한다. 추가 패키지·외부 런타임 요청은 없다.
- 분기·피드백·큐·모델 선택·신뢰도는 데이터/동작 계약이 없어 제외한다.
  공식 DataTable은 모델/가격 전용 예제이므로 기존 동적 SQL 표를 유지한다.
- 완료 조건: 위 기능의 실제 UI 연결, 오류/취소/편집/키보드/좁은 화면 회귀,
  npm test/build/lint, 계획·결정·출처 기록 갱신.


### 카탈로그 후속 검증 결과

- ErrorState, EditMessage, StoppedRun, RetrievalChunks, PromptLibrary를 실제 화면에
  연결했다. 공식 원본 SHA-256와 조정 사항은 Elements README에 기록했다.
- `npm test`: 31개 통과. 관련도 0/누락/범위 밖 값과 필터 후 prompt 선택 회귀 추가.
- `npm run build`: 성공. 기존 큰 청크 경고 유지(주 JS 약 1.20MB, gzip 371KB).
- `npm run lint`: 오류 0, 기존 Fast Refresh 경고 13개 유지.
- Chromium에서 실제 App + 제어 가능한 SSE/시각화 fixture로 다음을 확인했다.
  질문 검색·방향키·Enter·버튼 삽입, 빈 검색 결과, 자동 전송 없음, draft 보존,
  삽입 후 입력 포커스 복귀; 문서 출처·본문과 유효 관련도; 편집 답변 수·취소·
  fork 교체; 부분 답변 보존 후 중단·재실행; 오류 재실행과 실행 중 비활성화;
  연결 재시도 시 사용자 메시지 중복 없음; desktop 및 400px popover 범위.
- 기존 전송·복사·편집·재생성·도구 자동/수동 펼침·bar 차트·좁은 화면·수동 pane
  폭 유지·스트리밍 중 사용자 스크롤 보존·맨 아래 이동도 통과했다.
- `/tests/chat-browser.html`: lifecycle 10개 PASS. fixture에서 page error 및
  외부 요청 0. 실제 LLM·사내 서비스 연동은 이번 검증 범위에 포함하지 않았다.
- 브라우저 검증 중 중첩된 alert 역할을 제거해 오류를 한 번만 알리도록 했다.
- API·Backend·새 의존성 변경 없음. 결정 기록과 Todo 상태를 함께 갱신했다.
