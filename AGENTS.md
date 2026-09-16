# Production Planning Agent 작업 지침

이 저장소는 자연어로 제조 생산계획 데이터를 조회·분석·시뮬레이션하는
폐쇄망용 애플리케이션이다. `backend/`는 FastAPI와 Claude Agent SDK,
`frontend/`는 Vite·React SPA다.

## 작업 시작

- 먼저 [프로젝트 현황](plan/Todo.md)과 관련 상위 계획(`plan/`)을 확인한다.
- 기존 staged·unstaged·untracked 변경은 사용자의 작업으로 간주한다. 작업 목적을
  파악하기 전에는 되돌리거나 덮어쓰지 않고, 생성물·비밀값 여부를 확인한 뒤
  요청 범위에 속하는 파일만 수정한다.
- 코드나 문서를 수정할 대상 폴더에 더 가까운 `AGENTS.md`가 있으면 그 지침도
  읽고 함께 적용한다. 하위 지침은 해당 영역의 구체적인 규칙을 보완한다.
- 백엔드·프론트엔드에 걸친 작업은 루트 계획에서 계약과 완료 조건을 먼저
  확정하고 `backend/plan`, `frontend/plan`에 실행 작업을 나눈다.

## 공통 계약

- 최종 배포 환경은 인터넷이 차단된 폐쇄망이다. 외부 CDN·폰트·런타임 API에
  의존하지 말고, 새 의존성은 폐쇄망 반입 가능 여부를 먼저 검증한다.
- 비밀값, 사내 URL, 인증 정보는 코드·문서·예시 설정에 기록하지 않는다.
- `AgentEvent`, tool payload, Result Store, 시각화 명세 등 공유 계약을 바꾸면
  백엔드 스키마와 프론트엔드 타입·파서를 같은 작업에서 갱신한다.
- SQL 실행은 읽기 전용이어야 하며, mock과 real 서비스의 함수 시그니처와
  반환 형태를 동일하게 유지한다.
- 구조화 지식의 table·recipe는 `query_rules`, `aggregation_rules`,
  `visualization_hints`를 역할별로 구분한다. `sample_queries`는 데이터에 종속되는
  답변을 저장하지 않고 `question`, `sql`만 유지한다.
- 런타임 생산계획 Agent 지침인 `backend/agent/agent_sdk/CLAUDE.md`는 개발용
  저장소 지침과 별개다.

## 로컬 데이터와 산출물

- `.env*`, `.playwright-mcp/`, `artifacts/`, `backend/data/`, 로컬 SMT2020
  원본·생성 DB와 변환 스크립트는 Git에 포함하지 않는다. 이미 추적된 로컬
  산출물을 제외할 때는 파일을 지우지 말고 Git 추적만 해제한다.
- README의 실행 절차는 새 clone에서 필요한 파일과 별도 반입해야 하는 로컬
  자산을 구분한다. Git에 없는 데이터나 스크립트가 기본 제공되는 것처럼 쓰지 않는다.

## UI/UX 작업

- UI를 설계·구현·리뷰·수정할 때는 `ui-ux-pro-max` Skill을 우선
  활용해 접근성, 상호작용, 반응형 레이아웃과 시각적 일관성을 검토한다.
- 프론트엔드 UI 작업 전에는 `frontend/CLAUDE.md`의 프론트 디자인
  가이드를 함께 확인한다. Skill의 일반 권고와 충돌하면 사용자의
  명시적 요청, 더 가까운 `AGENTS.md`, `frontend/CLAUDE.md`, 기존 제품
  계약과 디자인 token 순으로 적용한다. Skill 결과를 근거로 확정된
  레이아웃·타이포그래피·색·아이콘·테마·스크롤 규칙을 자동으로
  대체하지 않는다.

## 지침 파일의 역할

- `AGENTS.md`는 Codex를 포함한 개발 에이전트의 저장소 작업 지침이다.
- 같은 위치의 `CLAUDE.md`가 `@AGENTS.md`를 포함하면 Claude Code가 동일한 개발
  지침을 재사용하기 위한 호환 진입점이다. 공통 규칙을 두 파일에 복제하지 않는다.
- `frontend/CLAUDE.md`의 추가 본문은 프론트 디자인 제약이고,
  `backend/agent/agent_sdk/CLAUDE.md`는 실행 중인 생산계획 Agent의 행동 지침이다.
  두 파일을 개발 지침이나 제품 런타임 지침으로 서로 대체하지 않는다.

## 문서 흐름

- `plan/Todo.md`: 프로젝트 전체 목표·범위·기능 상태와 완료한 일, 수행할 일,
  보류 항목을 함께 관리하는 단일 기준 문서다.
- `plan/<yymmdd>-<topic>-plan.md`: 개별 기능의 프론트엔드·백엔드 요구사항,
  공유 계약, 파트별 할당, 전체 완료 조건을 관리한다.
- `backend/plan`, `frontend/plan`: 상위 계획을 실행 가능한 파트별 Task와
  검증·결정 기록으로 나눈다. 완료 계획도 이력으로 남긴다.
- `backend/docs`, `frontend/docs`: 폐쇄망 이전·운영, 도메인 지식, 기술 결정 등
  반복해서 참고할 운영 문서를 둔다. 실행 일정과 Task는 두지 않는다.
- 작업 상태가 달라지면 관련 계획의 상태와 `plan/Todo.md`를 함께 갱신한다.
- `README.md`는 현재 사용자의 설치·실행·검증 진입점이다. 구현·환경변수·명령이
  바뀌면 루트와 해당 파트 README를 함께 확인한다.

## 기본 검증

- 백엔드: `cd backend && python -m pytest -q`
- 프론트엔드: `cd frontend && npm test && npm run build && npm run lint`
- 문서만 변경한 경우 링크, 파일명 규칙, `git diff --check`를 우선 검증한다.
