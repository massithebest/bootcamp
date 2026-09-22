# Production Planning Agent Backend

FastAPI와 Claude Agent SDK를 사용해 `AgentEvent`를 SSE로 전달하고 지식·SQL·
simulation·결과 저장·표·시각화 Tool을 제공한다. route는 요청 변환만 담당하며
업무 로직은 agent → tool → service 계층으로 분리한다.

## 설치

Python 3.11의 표준 `venv` 환경을 기준으로 한다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Windows PowerShell에서는 `py -3.11 -m venv .venv`와
`.\.venv\Scripts\Activate.ps1`을 사용한다. 폐쇄망 실행 환경은
[폐쇄망 배포 가이드](docs/CLOSED_NETWORK_SETUP.md)에 따라 개발 도구를 제외한
`requirements.txt`를 설치한다.

주요 환경변수는 다음과 같다.

- `ENV=dev|prod`: `prod`에서는 real service와 별도 운영 지식 경로를 강제
- `SERVICE_MODE=mock|real`: SQL·RAG·simulation service 선택. `prod`는 `real`만 허용
- `RESULT_UI_MODE=legacy|present`: 결과 표시 방식(기본 `legacy`). `present`는 bounded preview와
  flat `present_sql_preview`·`present_chart`·`present_table`·`present_simulation`,
  `/api/query-results/*`를 사용하고 `prepare_table`·`prepare_visualization`은 등록하지 않는다
- `LLM_PROVIDER`, `AGENT_MODEL`, provider key: 실제 Agent SDK 설정
- `KNOWLEDGE_DIR`, `KNOWLEDGE_DB_PATH`: 구조화 YAML과 텍스트 지식 SQLite 위치
- `KNOWLEDGE_SEARCH_BACKEND=local|service`: `search_documents`가 로컬 SQLite 또는 사내 RAG 어댑터를 쓸지 선택
- `KNOWLEDGE_MANAGEMENT_ENABLED`, `KNOWLEDGE_ALLOW_SELF_APPROVAL`, `KNOWLEDGE_PRINCIPALS`,
  `KNOWLEDGE_DEFAULT_PRINCIPAL`: 구조화 지식 변경 요청·승인의 스텁 권한 설정(값은 `.env.example` 참고)
- `RESULT_STORE_DIR`, `VISUALIZATION_STORE_DIR`: 조회 결과와 차트 명세 위치
- `CORS_ALLOW_ORIGINS`: 쿠키를 허용할 명시적 Frontend origin 목록

실제 값과 비밀값은 `.env`에만 두고 `.env.example`에는 넣지 않는다.

## 로컬 개발 자산

`datasets/`, `data/`, `scripts/`는 Git과 폐쇄망 반입 대상이 아니다.
`scripts/seed_local_documents.py`는 `datasets/rag_docs/**/*.md`를 텍스트 지식
저장소에 등록·검토·활성화하는 개발용 스크립트이며 반입 자산이 아니다.
폐쇄망의 텍스트 지식은 문서 관리 API로 등록한다.

### SMT2020

Mock SQL과 입력 검증 simulation은 HVLM/LVHM을 합친 SQLite DB를 사용한다.
원본 dataset, 생성 DB와 변환용 `scripts/build_smt2020_db.py`는 Git과 폐쇄망
반입 대상에서 제외되는 개발 전용 자산이다. 자산이 준비된 개발 환경에서만 다음을
실행한다.

```bash
python -m scripts.build_smt2020_db
```

두 benchmark의 ID가 겹치므로 SQL JOIN에는 업무 키와 `dataset`을 함께 사용한다.

## 실행 모드

기본 개발 모드:

```bash
SERVICE_MODE=mock uvicorn main:app --reload --port 8100
curl http://localhost:8100/health
```

`/api/chat`은 항상 실제 Claude Agent SDK를 호출하므로 `.env`에 provider와 CLI
설정이 필요하다. 지식·시각화 API와 `pytest`는 provider 없이 동작하며, 테스트는
SDK `query`를 대체해 Agent 이벤트 흐름을 검증한다. `services/real`은 폐쇄망 사내 DB·RAG·simulation 구현으로
교체하는 경계이며 mock과 함수 시그니처·반환 형태를 유지해야 한다.

폐쇄망 운영은 `ENV=prod`, `SERVICE_MODE=real`과 별도 `KNOWLEDGE_DIR`을 모두
요구한다. 조건을 충족하지 않으면 서버는 시작 단계에서 실패한다.

## API 진입점

- `POST /api/chat`: SSE 채팅과 Tool 실행 이벤트
- `GET /api/knowledge/tools|skills|entries|catalog|kpis`: Tool·Skill·구조화 지식 탐색
  (`catalog`·`kpis`는 활성 table·KPI 요약)
- `/api/knowledge/documents`: 텍스트 지식 등록·버전·검토·활성화 관리
- `/api/knowledge/changes`, `/validate`, `/guides/{kind}`, `/source/{kind}/{key}`: 구조화 YAML
  변경 요청·검증·승인. 직접 수정 API는 없고 승인된 변경만 `KNOWLEDGE_DIR` YAML에 반영
- `GET /api/me`: 현재 principal, 권한과 관리 기능 플래그
- `GET /api/visualizations/{visualization_id}`: 검증된 bar/line 차트 데이터(legacy)
- `GET /api/query-results/{result_id}/preview|table|chart`: 저장 결과의 bounded preview,
  저장된 최대 1,000건을 검색·정렬한 page 단위 표(≤100행), 서버 집계
  chart(bar/line/area, series ≤8·point ≤500). 없음·만료·타 세션은 동일한 404
- `GET /health`: 상태 확인

Result Store와 `prepare_table`, `prepare_visualization`, `/api/query-results/*`는 세션 범위 쿠키
`pp_session_scope`를 사용한다. 내부 파일 경로와 접근 scope는 모델 입력이나 Tool
payload에 노출하지 않는다.

## 지식 계약

`knowledge/` YAML이 table·KPI·recipe·scenario·simulation·glossary의 기준이다.

- `query_rules`: 기본 날짜·필터·정렬·조인 전제
- `aggregation_rules`: 결과 grain·집계 함수·중복·재집계 규칙
- `visualization_hints`: bar/line/표 선택을 위한 권고
- `sample_queries`: 데이터 값에 종속되지 않는 `question`, `sql` 예시

Agent는 SQL 작성 전 사용하는 table마다 `describe_table`을 호출한다. recipe를
사용하면 `get_recipe`의 CTE와 동일한 규칙을 함께 적용한다. 작성·검토 절차는
[도메인 지식 관리 지침](docs/domain-knowledge-management.md)을 따른다.

## 검증

```bash
python -m pytest -q
python -m pytest -m e2e  # 실제 CLI/provider 인증이 있는 환경에서만 실행
```

SMT2020 자산이 없으면 `smt2020` 테스트만 자동 skip된다. 번들 지식 YAML의 고정 값
(`wip`, `initial_wip` 등)을 단정하는 테스트는 `smt2020_bundle` 마커가 붙고
`bundled_knowledge` fixture로 `KNOWLEDGE_DIR`과 무관하게 번들 YAML을 읽는다.
폐쇄망에서 real 구현과 공통 계약만 검증할 때는 다음 프로필을 사용한다.

```bash
python -m pytest -q -m "not smt2020 and not smt2020_bundle and not mock_service and not e2e"
```

E2E가 아닌 공통 테스트가 외부 provider나 인터넷에 의존하도록 만들지 않는다.

## 참고

- [Backend 작업 지침](AGENTS.md)
- [폐쇄망 배포 및 실서비스 이식](docs/CLOSED_NETWORK_SETUP.md)
- [도메인 지식·테이블·CTE 관리](docs/domain-knowledge-management.md)
- [Backend 계획과 완료 이력](plan/Todo.md)
