# assistant-ui Elements 전환 실행 계획

- 상태: 완료
- 마지막 갱신: 2026-09-16
- 상위: [전환 계획](../../plan/260916-assistant-ui-elements-plan.md)
- Backend 계획: 없음(계약 미변경)
- 착수 조건: 공식 MCP·Skill·registry 및 기존 결정 확인 완료

## Task

1. `components/assistant-ui/elements`: 공식 Thread, ThreadList, ToolCall,
   AgentPlan 소스 구조를 한국어·기존 token에 맞게 조정한다. 설치된 0.15.19
   타입으로 검증하며 미지원 기능의 의존성은 가져오지 않는다.
2. `App`/`chat-window`: 루트 provider와 Thread 슬롯을 연결한다. 공통 메시지,
   composer, 액션을 Elements로 모으고 도메인 렌더러를 확장 슬롯으로 연결한다.
3. `app-sidebar`/`agent-progress`/`tool-result-card`: standalone Elements로
   교체한다. 예시 세션 안내, 실제 오류·취소 상태와 수동 펼침 상태를 보존한다.
4. `AGENTS.md`/`CLAUDE.md`/결정 기록: 요청 문구와 SSE 적용 예외, 변경된
   컴포넌트 경로, 대체된 결정을 기록한다.
5. npm test/build/lint, 브라우저 lifecycle, 입력·편집·재생성·중단·도구·차트·
   좁은 화면과 외부 요청을 검증한다. 새 disclosure의 오류/취소 회귀도 확인한다.

## 결정·실행 기록

- assistant-ui, elements, runtime, thread-list Skill을 참고했다.
- MCP list_templates/read_template(base-assistant-ui), Thread/ToolCall/AgentPlan
  문서와 첨부 llms index를 확인했다.
- 공식 registry 소스를 준비 환경에서 내려받아 검토했다. CLI 전체 설치는
  미사용 첨부·음성·shimmer 의존성을 추가하므로 필요한 소스만 조정한다.
- AgentPlan의 단일 activeIndex는 오류·취소를 표현하지 못하므로 명시적 단계
  상태를 받도록 확장한다. ToolCall은 문자열 결과 대신 ReactNode 슬롯과 오류
  상태를 추가해 기존 표/차트를 보존한다.

## 검증 결과

- `npm test`: 29개 통과(기존 27개 + 단계 상태·native disabled 회귀 2개).
- `npm run build`: 성공. 기존 500kB 이상 청크 경고는 남아 있다.
- `npm run lint`: 오류 0, 기존 ui/button·sidebar·tabs의 Fast Refresh 경고 3개.
- `/tests/chat-browser.html`: 기존 lifecycle 10개 모두 PASS.
- agent-browser로 기존 dev server를 열어 화면·DOM·오류를 확인했다.
- 별도 Chromium/Playwright에서 실제 App을 띄우고 제어 가능한 fetch SSE fixture로
  아래 흐름을 검증했다: 전송, tool 자동 펼침과 완료 후 접힘, 수동 접힘 유지,
  복사, 편집, 재생성, 취소, tool/backend 오류, 연결 실패 후 재시도와 사용자
  메시지 중복 방지. visualization 응답 fixture로 bar 차트 렌더링을 확인했다.
- 1440×1000 및 400×800 화면을 캡처해 검토했다. 가로 overflow 없음, 입력창
  및 액션 표시, 접힌 pane 포커스 제외, 900→905px 수동 pane 유지 확인.
- 긴 응답 스트리밍 도중 사용자가 위로 스크롤하면 위치를 유지하고,
  맨 아래로 이동 버튼으로 최신 응답에 도달하는 것을 확인했다.
- 브라우저 page error 0, fixture 시나리오에서 외부 network 요청 0.
- `git diff --check`와 변경 문서의 상대 링크 확인 통과.

### 검증 중 수정한 문제

- Base UI TooltipTrigger의 disabled는 tooltip 옵션이다. native 버튼 속성은
  공식 Base UI variant처럼 `render` 내부 버튼에 전달하도록 수정했다.
- Tailwind `--color-accent`가 프로젝트의 강조색 대신 shadcn의 옅은 배경을
  가리켜 전송·활성 탭이 흐려졌다. 프로젝트 accent/대비 텍스트 매핑을 복원했다.
- pane 폭 transition 도중 autosize가 임시로 좁은 폭을 측정했다. 입력 폭만
  관찰해 library autosize가 다시 측정하도록 했으며 텍스트·포커스 소유권은
  ComposerPrimitive에 유지했다.
- 새 대화·예시 세션 선택 시 이전 draft를 비운다. 취소·오류를 실제 runtime
  종료 상태에서 읽고, 최종 status가 오지 않은 단계는 `완료 미확인`으로 표시한다.

### 검증 범위의 한계

- LLM/실제 사내 서비스 연동은 이번 프론트엔드 전환에서 검증하지 않았다.
  브라우저 SSE·차트 검증은 명시적 fixture를 사용했다. backend 파일·계약과
  package.json/package-lock.json은 변경하지 않았다.
- 세션 영속화, 분기 탐색, 첨부·음성·Cloud와 floating modal은 현재 계약에
  없는 기능으로 추가하지 않았다. Inspector의 지식 조회·표·Result Store와
  chart marker 해석은 기존 도메인 구현을 유지한다.


## 후속: 공식 shadcn 명령 실행 (2026-09-16, 완료)

사용자가 지정한 아래 명령을 `frontend/`에서 실행했다.

```bash
npx shadcn@latest add @assistant-ui/thread @assistant-ui/thread-list
```

- 실행 전 현재 소스·package·lockfile을 임시 백업했다. 기존 파일 덮어쓰기
  질문에는 no로 응답했다. Thread, Markdown chart 확장, 기본 UI는 보존한다.
- CLI가 파일 12개를 추가했다: runtime ThreadList, attachment, image, file,
  follow-up suggestions, reasoning, tool group/fallback, avatar 및 보조 훅.
- 직접 의존성 `tw-shimmer@0.4.13`, `zustand@5.0.15`를 정확한 버전으로 고정했다.
  lockfile 비교 결과 새 package는 tw-shimmer 하나이며 zustand는 기존 전이
  의존성의 직접 선언이다. 기존 package 버전 변경은 없다.
- CSS shimmer import 및 collapse animation/variant가 추가됐다.
- 생성 소스의 React 19식 ref를 React 18 forwardRef로 조정하고, 기존
  TooltipIconButton에 공식 side/variant/size 인터페이스를 보완했다.
  빈 catch에는 fallback 의도를 기록하고 적용되지 않는 eslint 주석을 제거했다.
- runtime ThreadList 소스는 설치했지만 실제 세션 adapter가 없어 화면의
  standalone 예시 목록을 대체하지 않는다. 첨부·reasoning 등도 설치 자체로
  활성화하지 않는다. provider와 API 계약은 그대로다.
- 검증: 테스트 29개, build, 기존 화면의 Chromium 상호작용 fixture 모두 통과.
  lint 오류 0, 경고 13(기존 3 + 생성 컴포넌트의 혼합 export 경고 10).
  기존 청크 크기 경고는 남아 있다.


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
