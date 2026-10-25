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

- `ENV=dev|prod`: `prod`에서는 production service와 별도 운영 지식 경로를 강제
- `SERVICE_MODE=mock|production`: SQL·RAG·simulation service 선택. `real`은 호환 별칭이며
  `prod`는 `production`을 사용
- `API_TIMEOUT_SECONDS=60`: 폐쇄망 production API 요청 timeout(초). production adapter에서 사용할 설정이며 현재는 미사용
- 결과 표시는 bounded preview와 flat `present_sql_preview`·`present_chart`·
  `present_table`·`present_simulation` Tool, `/api/query-results/*`만 사용한다
- `LLM_PROVIDER`, `AGENT_MODEL`, provider key: 실제 Agent SDK 설정
- `KNOWLEDGE_DIR`, `KNOWLEDGE_DB_PATH`: 구조화 YAML과 텍스트 지식 SQLite 위치. 개발 기본값은
  `knowledge/mock`, 폐쇄망 반입 YAML 기본 위치는 `knowledge/production`
- `KNOWLEDGE_SEARCH_BACKEND=local|service`: `search_documents`가 로컬 SQLite 또는 사내 RAG 어댑터를 쓸지 선택.
  `local`은 검토·활성화된 문서를 제목·문단 기준 400자 청크(80자 겹침)로 색인하고, 키워드 점수와 문자 n-gram 해싱
  임베딩(2048차원, `services/knowledge/embedding.py`)의 코사인 유사도를 더해 찾는 PoC 하이브리드 검색이다. 벡터는
  지식 SQLite의 `chunks` 테이블에 두며 모델 다운로드가 없다. 동의어 같은 의미 검색은 하지 못하므로 운영 임베딩은
  `get_embedder()`를 교체해 연결한다
- `KNOWLEDGE_MANAGEMENT_ENABLED`, `KNOWLEDGE_ALLOW_SELF_APPROVAL`, `KNOWLEDGE_PRINCIPALS`,
  `KNOWLEDGE_DEFAULT_PRINCIPAL`: 구조화 지식 변경 요청·승인의 스텁 권한 설정(값은 `.env.example` 참고)
- `RESULT_STORE_DIR`: 조회 결과 저장 위치
- `CORS_ALLOW_ORIGINS`: 쿠키를 허용할 명시적 Frontend origin 목록

실제 값과 비밀값은 `.env`에만 두고 `.env.example`에는 넣지 않는다.

## 로컬 개발 자산

`data/`는 Git과 폐쇄망 반입 대상이 아니다(생성되는 SQLite 파일이 담긴다).
`scripts/`는 실제 데이터를 다루지 않는 순수 코드이므로 Git에 포함되며 어떤
환경에서도(폐쇄망 포함) 그대로 실행할 수 있다.

### 합성 mock 데이터

Mock SQL과 입력 검증 simulation은 `scripts/generate_mock_database.py`가 매번
결정적(seed 고정)으로 생성하는 SQLite DB(SEG_A/SEG_B 두 생산 세그먼트)를
사용한다. 외부 원본 파일이 필요 없다.

```bash
python -m scripts.generate_mock_database
python -m scripts.generate_mock_documents   # RAG mock 검색용 일반 생산계획 용어집
```

두 세그먼트의 ID가 겹치므로 SQL JOIN에는 업무 키와 `dataset`을 함께 사용한다.
폐쇄망의 텍스트 지식은 이 생성 스크립트 대신 문서 관리 API로 등록한다.

## Service 디렉터리

- `services/knowledge`: YAML 카탈로그, 문서 저장소, 변경 승인과 검색(청킹·해싱 임베딩은 `embedding.py`)
- `services/results`: Result Store, 결과 조회·차트 투영·표시 검증
- `services/sql/guard.py`: mock과 production이 공유하는 읽기 전용 SQL 가드
- `services/simulation`: 공통 시뮬레이션 정의와 입력 검증
- `services/mock` / `services/production`: 실행 모드별 SQL·RAG·simulation 구현
- `services/service_logging.py`: 공통 서비스 로깅

## 실행 모드

기본 개발 모드:

```bash
SERVICE_MODE=mock uvicorn main:app --reload --port 8100
curl http://localhost:8100/health
```

`/api/chat`은 항상 실제 Claude Agent SDK를 호출하므로 `.env`에 provider와 CLI
설정이 필요하다. `LLM_PROVIDER`는 `anthropic`, `openrouter`, `azure_openai`, `local`
중 하나다. `azure_openai`는 Azure OpenAI 호환 게이트웨이(GPT 계열 deployment)를 쓰며,
CLI의 Anthropic 형식 요청을 백엔드 `/anthropic` 프록시가 chat completions로 변환한다.
프록시는 서버 프로세스마다 새로 만든 토큰을 가진 CLI 요청만 받으므로 `BACKEND_PORT`가
`--port`와 같아야 한다. 설정 항목은 `.env.example`의 `AZURE_OPENAI_*`를 따른다. 지식·시각화 API와 `pytest`는 provider 없이 동작하며, 테스트는
SDK `query`를 대체해 Agent 이벤트 흐름을 검증한다. `services/production`은 폐쇄망
사내 DB·RAG·simulation 구현으로 교체하는 경계이며 mock과 함수 시그니처·반환 형태를
유지해야 한다.

폐쇄망 운영은 `ENV=prod`, `SERVICE_MODE=production`과 명시적인 `KNOWLEDGE_DIR`을 모두
요구한다. 운영 YAML은 `knowledge/production`에 반입해 지정하거나 별도 영속 경로에
두며, `knowledge/mock`은 지정할 수 없다. 조건을 충족하지 않으면 서버는 시작 단계에서
실패한다.

## API 진입점

- `POST /api/chat`: SSE 채팅과 Tool 실행 이벤트
- `GET /api/knowledge/tools|skills|entries|catalog|kpis`: Tool·Skill·구조화 지식 탐색
  (`catalog`·`kpis`는 활성 table·KPI 요약)
- `/api/knowledge/documents`: 텍스트 지식 등록·버전·검토·활성화 관리
- `/api/knowledge/changes`, `/validate`, `/guides/{kind}`, `/source/{kind}/{key}`: 구조화 YAML
  변경 요청·검증·승인. 직접 수정 API는 없고 승인된 변경만 `KNOWLEDGE_DIR` YAML에 반영
- `GET /api/me`: 현재 principal, 권한과 관리 기능 플래그
- `GET /api/query-results/{result_id}/preview|table|chart`: 저장 결과의 bounded preview,
  저장된 최대 1,000건을 검색·정렬한 page 단위 표(≤100행), 서버 집계
  chart(bar/line/area, series ≤8·point ≤500). 없음·만료·타 세션은 동일한 404
- `GET /health`: 상태 확인

Result Store와 `/api/query-results/*`는 세션 범위 쿠키 `pp_session_scope`를
사용한다. 내부 파일 경로와 접근 scope는 모델 입력이나 Tool payload에 노출하지
않는다.

## 지식 계약

`knowledge/mock/`은 개발·회귀용 YAML이고, `knowledge/production/`은 폐쇄망 이식용
운영 YAML 위치다. 실행 중인 `KNOWLEDGE_DIR`의 YAML이 table·KPI·recipe·scenario·
simulation·glossary의 단일 기준이다.

- `query_rules`: 기본 날짜·필터·정렬·조인 전제
- `aggregation_rules`: 결과 grain·집계 함수·중복·재집계 규칙
- `visualization_hints`: bar/line/표 선택을 위한 권고
- `sample_queries`: 데이터 값에 종속되지 않는 `question`, `sql` 예시

Agent는 SQL 작성 전 사용하는 table마다 `describe_table`을 호출한다. recipe를
사용하면 `get_recipe`의 CTE와 동일한 규칙을 함께 적용한다. 작성·검토 절차는
[도메인 지식 관리 지침](docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md)을 따른다.

## 검증

```bash
python -m pytest -q
python -m pytest -m e2e  # 실제 CLI/provider 인증이 있는 환경에서만 실행
```

합성 mock DB 생성기를 사용하는 테스트는 `mock_service` 마커가 붙는다(항상 실행).
번들 지식 YAML의 고정 값(`wip`, `initial_wip` 등)을 단정하는 테스트는
`bundled_knowledge` 마커가 붙고 같은 이름의 fixture로 `KNOWLEDGE_DIR`과 무관하게
번들 YAML을 읽는다. 폐쇄망에서 production 구현과 공통 계약만 검증할 때는 다음
프로필을 사용한다.

```bash
python -m pytest -q -m "not bundled_knowledge and not mock_service and not e2e"
```

E2E가 아닌 공통 테스트가 외부 provider나 인터넷에 의존하도록 만들지 않는다.

### Agent 정량 평가

`evals/agent_eval_set.yaml`의 고정 질문으로 실제 Agent를 실행해 정답률·완료율·응답
시간·조회 규칙 준수·출처 표기·쓰기 SQL 시도·후속질문 제공률·비용을 계산한다. 정답은
질문마다 `truth_sql`로 합성 mock DB에서 다시 계산한다. LLM 인증이 필요하며 결과는
저장소 루트 `artifacts/evals/`에 남는다(Git 제외). `LLM_PROVIDER=azure_openai`면 스크립트가
`/anthropic` 프록시를 같은 프로세스 안에 빈 포트로 띄우므로 실행 중인 Backend가 없어도 된다.
"조회 데이터 정답률"은 SQL 결과 행에 정답 값이 그대로 있는지 보는 보조 지표라, 세분화해 조회한
뒤 답변에서 합산하면 최종 답변이 맞아도 불일치로 잡힐 수 있다. 질문당 비용은 CLI가 Claude 요금표로
추정한 값이라 GPT 게이트웨이의 실제 과금과 다를 수 있다.

```bash
python -m scripts.evaluate_agent
python -m scripts.evaluate_agent --static-only  # 지식 검증률·SQL 가드 차단율만, LLM 불필요
```

## 참고

- [Backend 작업 지침](AGENTS.md)
- [폐쇄망 배포 및 실서비스 이식](docs/CLOSED_NETWORK_SETUP.md)
- [도메인 지식·테이블·CTE 관리](docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md)
- Backend 계획: [할 일·아이디어](plan/Todo.md) · [진행 중·현재 계약](plan/InProgress.md) · [완료 이력](plan/History.md)
