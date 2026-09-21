# Backend 작업 지침

Python 3.11 FastAPI 서비스다. `main.py`가 앱을 만들고 `/api/chat`은 Claude Agent
SDK 이벤트를 SSE로 전달한다. 코드 변경 전 `plan/Todo.md`와 대상
폴더의 더 가까운 `AGENTS.md`를 확인한다. 이 workspace는 Frontend나
루트 계획 문서를 읽을 수 있다고 가정하지 않는다.

## 작업과 계획

- 기존 staged·unstaged·untracked 변경은 사용자 작업으로 간주하고 요청 범위
  밖 파일을 되돌리거나 덮어쓰지 않는다.
- 작은 계획은 `plan/Todo.md`에 직접 작성하고, 큰 작업만 `plan/`에
  날짜형 파일로 만든다. 외부 소비자 계약은 문서 안에 자체적으로 적는다.
- 폐쇄망 환경을 기준으로 하며 외부 CDN·런타임 API, 비밀값·사내 URL을
  코드·로그·문서에 추가하지 않는다.

## 계층과 계약

- 흐름은 route → agent → SDK tool → tool → service → DB/외부 provider 순서다.
  route에는 SQL, provider 설정, 시각화 검증과 업무 로직을 넣지 않는다.
- `api/schemas.py`가 API 계약, `agent/event_adapter.py`가 SDK 이벤트 변환,
  `agent/sdk_tools.py::TOOL_NAMES`가 등록 tool 목록의 기준이다.
- `agent/system_prompt.py`에는 짧은 역할·안전 원칙, 런타임
  `agent/agent_sdk/CLAUDE.md`에는 Tool/Skill 인덱스와 공통 절차,
  `.claude/skills/*/SKILL.md`에는 업무별 실행 절차만 둔다. 스키마와 업무 정의를
  이 세 계층에 복제하지 않는다.
- `knowledge/` YAML이 catalog, join, KPI, recipe/CTE, simulation, glossary와
  scenario의 source of truth다. 로드·검증은 `services/knowledge_service.py`,
  Agent 접근은 등록된 지식 tool을 통한다.
- table과 recipe의 `query_rules`는 기본 날짜·필터·정렬·조인 전제,
  `aggregation_rules`는 grain·집계 함수·중복·재집계 규칙,
  `visualization_hints`는 표현 권고를 담는다. table/recipe의 `sample_queries`는
  `question`, `sql`만 허용하며 현재 데이터 값인 `answer`를 저장하지 않는다.
- SQL은 `services/sql_guard.py`의 읽기 전용 검사를 통과해야 한다. Mock의 DB
  authorizer와 read-only 연결을 유지하고, real 구현도 DB 권한과 실행 계층에서
  쓰기를 차단한다. 카탈로그 스키마 변경 시 YAML, 시드 스크립트와 테스트를
  함께 갱신한다.
- `services/mock`과 `services/real`의 함수 시그니처와 결과 형태를 같게 유지하고
  mock 구현을 삭제하지 않는다.

## Agent와 결과 처리

- 안정적인 `AgentEvent` 종류는 `text`, `status`, `tool_call`, `tool_result`,
  `error`, `done`이다. 성공한 `done.data.turn_id`와
  `ChatRequest.fork_from_turn_id`의 포크 계약을 유지한다.
- 같은 업무 Tool 호출의 `tool_call`, 연결된 `status`, `tool_result`는 동일한
  `tool_call_id`를 사용한다. `tool_call.data.args`에는 공개 가능한 모델 입력만
  넣고 access scope, provider 설정과 내부 SDK 이벤트는 노출하지 않는다.
- partial `text_delta`만 `text`로 전달하고 같은 provider message의 최종 누적
  `TextBlock`을 중복 전송하지 않는다. thinking/signature/불완전 tool JSON은
  공개 이벤트로 변환하지 않는다.
- 포크 anchor에는 transcript에 존재하는 `AssistantMessage` 또는 `UserMessage`
  UUID만 사용한다. `ResultMessage.uuid`를 `resume_session_at`에 전달하지 않는다.
  fork ID 생략은 계속 진행, 빈 문자열은 새 대화, 알 수 없는 ID는 오류 후 안전한
  새 대화 fallback이라는 구분을 유지한다.
- streaming 오류는 내부 예외를 숨기고 `error` 다음 `done` 이벤트를 보낸다.
- 조회 결과는 `services/result_store.py`로 저장하며 내부 parquet 경로를 tool
  payload에 노출하지 않는다.
- 차트는 `prepare_visualization`이 실제 `result_id`와 grain을 검증해 등록한다.
  `/api/visualizations/{id}`만 조회 진입점으로 사용하고 SQL·시뮬레이션 결과에
  자동 차트를 붙이지 않는다.
- 독립 표는 `prepare_table`이 실제 `result_id`, access scope와 선택 컬럼을
  검증해 최대 100행만 반환한다. 원본 행 배열을 모델 입력으로 받지 않는다.
- 표 요청 또는 Markdown 표 응답에서 모델이 호출을 빠뜨리면 `run_agent`가 마지막
  접근 가능한 Result Store 결과로 `prepare_table` 이벤트를 보완한다.
- 환경변수는 `core/config.py`에서만 읽는다. 새 키는 실제 값 없이
  `.env.example`에도 추가한다.
- 작성형 텍스트 지식은 `services/document_store.py`의 로컬 SQLite에서 버전·검토·
  활성화 상태를 관리한다. 구조화 YAML은 계속 읽기 전용이며 두 저장소를 섞어
  수정하지 않는다.

## 폐쇄망과 지식 관리

- 의존성·provider·환경·배포 또는 real 서비스 작업 전
  [폐쇄망 배포 및 이식 가이드](docs/CLOSED_NETWORK_SETUP.md)를 읽는다.
- table, KPI, recipe/CTE, RAG 지식을 추가하거나 검토할 때는
  [도메인 지식 관리 지침](docs/domain-knowledge-management.md)을 따른다.
- 로컬 `datasets/`, `data/`, `.env`, 변환용 `scripts/`는 배포 저장소에 자동으로
  포함되지 않는다. 테스트 fixture와 달리 운영·benchmark 자산이 필요한 명령은
  해당 파일의 별도 반입 여부를 먼저 확인한다.
- API 키, 비밀번호, 사내 URL을 코드·로그·문서·예시 설정에 넣지 않는다.

## 명령과 검증

`backend/`에서 실행한다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.build_smt2020_db
PLANNING_AGENT_FAKE=1 python -m uvicorn main:app --reload --port 8100
python -m pytest -q
python -m pytest -m e2e
```

Windows PowerShell에서는 `py -3.11 -m venv .venv`로 만들고
`.\.venv\Scripts\Activate.ps1`로 활성화한다. 에이전트의 테스트 도구까지 필요한
개발 환경이므로 여기서는 `requirements-dev.txt`를 설치하며, 폐쇄망 실행 환경은
`docs/CLOSED_NETWORK_SETUP.md`에 따라 `requirements.txt`만 설치한다.

- 기본 테스트는 mock 서비스와 fake runner를 우선한다. E2E는 실제 CLI/provider
  인증이 필요한 동작에만 사용한다.
- 새 tool은 wrapper, 런타임 지침, prompt 정합성 테스트, fake runner와
  프론트 renderer/toolkit 필요 여부를 함께 갱신한다. 입력 기본값과 선택 필드는
  업무 함수 시그니처와 MCP 광고 JSON Schema에서 같은 의미여야 한다.
- 현재 별도 linter, formatter와 coverage 기준은 없다. 설정 없이 필수라고
  문서화하지 않는다.
