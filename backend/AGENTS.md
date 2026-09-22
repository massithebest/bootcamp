# Backend 작업 지침

Python 3.11 FastAPI 서비스다. `/api/chat`은 Claude Agent SDK 이벤트를
`AgentEvent` SSE로 변환한다. 작업 전 `plan/Todo.md`와 대상 폴더의 더 가까운
`AGENTS.md`를 확인한다.

## 경계

- 흐름은 route → agent → SDK tool → tool → service → DB/provider 순서다.
  route에 SQL, provider 설정, 결과 검증과 업무 로직을 넣지 않는다.
- API 계약은 `api/schemas.py`, 이벤트 변환은 `agent/event_adapter.py`, 등록 Tool은
  `agent/sdk_tools.py`, 구조화 지식은 `knowledge/` YAML을 기준으로 한다.
- SQL은 `services/sql_guard.py`를 통과한 읽기 전용 쿼리만 허용한다.
  `services/mock`과 `services/real`의 공개 시그니처·반환 형태를 맞춘다.
- 환경변수는 `core/config.py`에서 읽고 새 키는 비밀값 없이 `.env.example`에 추가한다.
- 폐쇄망·real service 작업은 `docs/CLOSED_NETWORK_SETUP.md`, 지식 작업은
  `docs/domain-knowledge-management.md`를 먼저 확인한다.

## Agent와 결과 계약

- 공개 이벤트는 `text`, `status`, `tool_call`, `tool_result`, `error`, `done`이다.
  같은 호출은 동일한 `tool_call_id`를 쓰고 모델 thinking·내부 경로·scope·provider
  설정을 노출하지 않는다.
- 성공한 `done.data.turn_id`만 포크 anchor로 사용한다. 오류 스트림도 `error` 다음
  `done`으로 종료한다.
- `RESULT_UI_MODE=legacy`는 `prepare_table`·`prepare_visualization`, `present`는
  bounded preview와 flat `present_*` Tool 및 `/api/query-results/*`를 사용한다.
  모드를 바꾸면 Tool 등록, payload, 런타임 지침, Frontend fixture를 함께 갱신한다.
- 구조화 YAML은 변경 요청 승인 경로로만 수정한다. 권한 검사는
  `core/principal.py`에 두며 현재 principal 구현은 보안 경계가 아니다.

## 런타임 지침 계층

- `agent/system_prompt.py`: 짧은 역할·안전 원칙.
- `agent/agent_sdk*/CLAUDE.md`: Tool·Skill 인덱스와 공통 규칙.
- `agent/agent_sdk*/.claude/skills/*/SKILL.md`: 업무별 절차.

스키마와 업무 정의를 여러 계층에 복제하지 않는다. Tool을 바꾸면 wrapper,
지침, prompt 정합성 테스트와 소비자 renderer 필요 여부를 함께 확인한다.

## 작업과 검증

- 기존 변경을 보존하고 작은 작업은 `plan/Todo.md`, 큰 작업만
  `plan/<yymmdd>-<topic>-plan.md`에 기록한다.
- 로컬 `datasets/`, `data/`, `.env`, 변환 스크립트와 비밀값은 커밋하지 않는다.
- 기본 검증: `source .venv/bin/activate && python -m pytest -q`
- 실제 CLI/provider가 필요한 경우에만 `python -m pytest -m e2e`를 실행한다.
