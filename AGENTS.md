# Production Planning Agent 작업 지침

폐쇄망에서 제조 생산계획 데이터를 조회·분석·시뮬레이션하는 애플리케이션이다.
`backend/`는 FastAPI·Claude Agent SDK, `frontend/`는 Vite·React SPA다.

## 작업 원칙

- 작업 전 해당 workspace의 `plan/Todo.md`와 더 가까운 `AGENTS.md`를 읽는다.
- 기존 staged·unstaged·untracked 변경은 사용자 작업으로 보고 요청 범위 밖의
  변경을 되돌리거나 덮어쓰지 않는다.
- Backend와 Frontend 계획은 각자의 `plan/`에서 독립적으로 관리한다. 공유 계약을
  바꾸면 양쪽 구현·테스트·계획에 같은 입력·출력·오류 의미를 반영한다.
- 최종 환경은 인터넷이 차단된다. 외부 CDN·폰트·런타임 API에 의존하지 않고,
  비밀값·사내 URL·인증 정보를 코드와 문서에 남기지 않는다.

## 공통 계약

- SQL과 production/mock service는 읽기 전용이며 공개 함수의 시그니처와 반환 형태를 맞춘다.
- `AgentEvent`, Tool payload, Result Store와 결과 UI 계약은 소비자와 함께 변경한다.
- 구조화 지식은 `query_rules`, `aggregation_rules`, `visualization_hints`의 역할을
  구분하고 `sample_queries`에는 `question`, `sql`만 둔다.
- `.env*`, `.playwright-mcp/`, `artifacts/`, `backend/data/`(생성된 합성 mock
  SQLite 포함)는 Git 및 폐쇄망 반입 대상이 아니다. README에는 Git 포함 자산과
  별도 반입 자산을 구분한다.

## UI 작업

- UI 작업은 디자인 Skill과 `frontend/docs/assistant-ui-design.md`,
  `frontend/docs/decisions.md`를 확인한다. 디자인 Skill은 Codex에서는
  `ui-ux-pro-max`, Claude Code에서는 `frontend-design`을 사용한다. 확정된 제품 계약과 semantic token을
  일반적인 디자인 권고로 임의 교체하지 않는다.
- Frontend는 데스크톱 전용이다. 1280px 이상에서 검증하며 모바일 viewport,
  device emulation, 터치 전용 요구사항을 추가하지 않는다.

## 문서 역할

- `AGENTS.md`: 개발 에이전트가 지킬 경계와 검증.
- `CLAUDE.md`: 같은 위치의 `AGENTS.md`를 재사용하는 Claude Code 진입점.
- `backend/agent/agent_sdk*/CLAUDE.md`: 개발 지침이 아니라 런타임 Agent 지침.
- `README.md`: 사용자의 설치·실행·검증 진입점.
- `*/plan/Todo.md`: 현재 계약·다음 작업·완료 이력의 기준.
- `*/docs/`: 반복해서 참고하는 운영·설계 문서. 일정과 체크리스트는 두지 않는다.
- `*/docs/`에 새로 작성하는 문서의 파일명은 대문자로 쓴다. 기존 문서를 이동하거나
  이름을 바꾸면 README·계획·코드 주석의 링크도 함께 갱신한다.

## 기본 검증

- 실행: Backend `SERVICE_MODE=mock uvicorn main:app --reload --port 8100`,
  Frontend `npm run dev` (3100, strictPort). 합성 mock DB는 `backend/`에서
  `python -m scripts.generate_mock_database`로 생성한다.
- Backend: `cd backend && source .venv/bin/activate && python -m pytest -q`
- Frontend: `cd frontend && npm test && npm run build && npm run lint`
- 문서만 변경하면 링크·명령·파일명과 `git diff --check`를 확인한다.
