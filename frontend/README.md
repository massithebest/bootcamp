# Production Planning Agent Frontend

Backend의 SSE `AgentEvent`를 표시하는 Vite 7·React 18·strict TypeScript 기반
3-pane Agent Workbench다. Backend는 기본적으로 `http://localhost:8000`,
Frontend는 `http://localhost:3000`을 사용한다.

## 주요 화면과 기능

- Sidebar: 새 채팅, 현재 실행의 최근 대화, 지식 관리 진입
- Chat: streaming 답변, 공개 실행 단계, Tool 상세, 편집·재생성·중단·복사
- Context Inspector: Tool·Skill·지식의 읽기 전용 컨텍스트
- Knowledge Manager: 구조화 YAML 조회와 버전형 텍스트 지식 관리
- Standalone Table: 최대 100행 검색·정렬·페이지 이동
- Visualization: Backend가 검증한 bar·line 차트와 데이터 표 대안

채팅 UI는 `@assistant-ui/react`의 `ExternalStoreRuntime`을 사용한다. 브라우저는
`fetch`/`ReadableStream`으로 Backend SSE를 직접 읽으며 외부 LLM provider를
호출하지 않는다.

## 설치와 실행

정확한 lockfile 버전을 사용한다.

```bash
npm ci
cp .env.example .env.local
npm run dev
```

`.env.local`의 `VITE_API_BASE_URL`을 Backend 주소로 설정한다. `.env.local`은
Git에 포함하지 않는다.

## 주요 구조

- `src/components/assistant-ui/elements`: 반입 후 프로젝트에 맞게 조정한 Elements
- `src/components/chat`: 채팅·Tool 결과·표·차트 기능 UI
- `src/components/knowledge`: 지식 탐색·관리와 구조화 상세
- `src/hooks`: Agent 채팅과 화면 상태
- `src/lib`: SSE, API, runtime adapter와 결과 검증
- `src/types`: Backend와 공유하는 클라이언트 계약

구조화 지식 상세는 `query_rules`, `aggregation_rules`, `visualization_hints`를
각각 조회 규칙·집계 규칙·시각화 안내로 표시한다. table/recipe의 샘플은 질문과
SQL만 표시하며 실행 결과를 문서 값처럼 만들지 않는다.

## 검증

```bash
npm test
npm run build
npm run lint
npm run preview
```

`npm test`는 Node 내장 테스트 실행기와 Vite/TypeScript로 SSE 파서·전송,
메시지 상태 전이, Tool 결과와 구조화 지식 렌더링을 검증한다. production build가
TypeScript 검사를 포함한다.

개발 서버에서 다음 독립 페이지로 실제 React·assistant-ui lifecycle을 확인한다.

- `/tests/chat-browser.html`: retry/cancel/edit/regenerate와 메시지 순서
- `/tests/knowledge-browser.html`: 지식 목록·상세·관리 흐름
- `/tests/workbench-browser.html`: pane, focus, resize와 Workbench 상호작용

브라우저 자동화 결과는 `.playwright-mcp/` 또는 `artifacts/`에 두며 커밋하지
않는다. 테스트 페이지의 mock은 해당 페이지 안에서만 동작하고 production
bundle에는 포함되지 않는다.

## 현재 제약

- 세션 목록은 현재 실행 동안의 예시 상태이며 영속 저장소가 아니다.
- Composer의 첨부·모델 선택·추론 강도 제어는 표시만 제공하는 비활성 UI다.
- 새 응답은 standalone Tool UI를 사용하며 과거 chart marker는 호환용으로만 읽는다.
- 모바일 전용 UX는 범위 밖이지만 좁은 화면의 pane 접힘과 가로 overflow는 보호한다.

## 참고

- [Frontend 작업 지침](AGENTS.md)
- [Frontend 디자인 가이드](CLAUDE.md)
- [기술 결정 기록](docs/decisions.md)
- [폐쇄망 운영 원칙](docs/closed-network.md)
- [Frontend 실행 계획](plan/)
- [전체 기능 계획](../plan/)
