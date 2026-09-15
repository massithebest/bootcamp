# Production Planning Agent 작업 지침

이 저장소는 자연어로 제조 생산계획 데이터를 조회·분석·시뮬레이션하는
폐쇄망용 애플리케이션이다. `backend/`는 FastAPI와 Claude Agent SDK,
`frontend/`는 Vite·React SPA다.

## 작업 시작

- 먼저 [프로젝트 현황](plan/Todo.md)과 관련 상위 계획(`plan/`)을 확인한다.
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
- 런타임 생산계획 Agent 지침인 `backend/agent/agent_sdk/CLAUDE.md`는 개발용
  저장소 지침과 별개다.

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

## 기본 검증

- 백엔드: `cd backend && python -m pytest -q`
- 프론트엔드: `cd frontend && npm run build && npm run lint`
- 문서만 변경한 경우 링크, 파일명 규칙, `git diff --check`를 우선 검증한다.
