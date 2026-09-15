# 폐쇄망 배포 & pntfp 이식 가이드

이 문서는 **인터넷이 되는 환경에서 준비물을 챙긴 뒤, 폐쇄망 PC로 코드를
이전해서 백엔드를 기동하고, 최종적으로 pntfp의 실제 서비스 로직(SQL/RAG/
Simulation)을 이식하기까지**의 절차를 두 단계로 정리한다.

```text
Part 1. 폐쇄망 인프라 구축        Part 2. pntfp 서비스 로직 이식
  준비물 챙기기 → 반입              services/real/* 스텁을 실제 로직으로 교체
  → 의존성 설치 → .env 구성          (SERVICE_MODE=mock → real)
  → mock 기동 검증
```

Part 1을 마쳐 `SERVICE_MODE=mock`으로 서버가 정상 기동하는 것을 확인한
뒤에 Part 2로 넘어간다. Part 2는 Claude Code에게 이 문서 경로를 알려주고
"이 가이드를 보고 이식해줘"라고 지시하는 방식으로 실행하면 된다.

---

# Part 1. 폐쇄망 인프라 구축

## 1-0. 전체 흐름

```text
[인터넷 환경]                          [폐쇄망 환경]
1. 소스 코드 확보                       4. 소스 코드 반입
2. Python 의존성 오프라인 번들 준비  →  5. 의존성 오프라인 설치
3. Claude CLI(Node.js) 바이너리 준비     6. .env 구성
                                        7. 서버 기동 + 헬스체크
```

폐쇄망에는 `pip install`, `npm install`, `conda env create`가 인터넷을 거쳐
동작하지 않는다는 전제로 모든 단계를 "미리 받아서 옮기는" 방식으로 짠다.

## 1-1. 인터넷 환경에서 준비할 것

### 소스 코드

- 이 저장소(`production-planning-agent`) 전체를 클론/압축한다.
- `.git` 히스토리가 필요 없다면 `git archive`로 워킹트리만 내보내도 된다.
  히스토리가 필요하면 `.git` 폴더까지 통째로 옮긴다.
- `node_modules`, `__pycache__`, `dist`(frontend 빌드 산출물) 등
  빌드 산출물/캐시는 제외한다 (폐쇄망 쪽에서 다시 만든다).

### Python 의존성 오프라인 번들

폐쇄망에 PyPI 미러(Nexus/Artifactory 등)가 없다는 전제로, `pip download`로
wheel을 미리 받아둔다.

```bash
cd backend
python -m venv /tmp/offline-build && source /tmp/offline-build/bin/activate
pip download -r requirements-dev.txt -d ./offline-packages \
  --platform manylinux2014_x86_64 --python-version 311 --only-binary=:all:
```

- `--platform`/`--python-version`은 **폐쇄망 PC의 OS/Python 버전에 맞춘다**
  (다르면 wheel이 안 맞아 설치가 실패한다). 폐쇄망 PC가 이 빌드 환경과
  동일 OS/아키텍처가 아니면 그 환경에서 직접 받는 것이 가장 안전하다.
- 사내 PyPI 미러가 이미 있다면 이 단계는 생략하고 1-5에서 미러를 가리키면 된다.
- `requirements.txt`의 각 패키지가 **사내에서 사용 가능한 이름/버전인지
  사전 확인**한다. 특히 아래는 원래 pntfp 환경 기준으로 들어간 항목이라
  폐쇄망 사내 표준과 다를 수 있다 — 다르면 실제 이식 시(Part 2) 맞춰 교체한다:
  - `langchain`, `langchain-openai` (LLM 연동 방식이 사내 표준과 다르면 교체)
  - `pymilvus` (사내 Milvus 서버 버전과 클라이언트 버전이 맞아야 함)

### Claude Agent SDK 실행 바이너리 (Node.js + Claude Code CLI)

`claude-agent-sdk`(Python 패키지)는 **Node.js 런타임과 `claude` CLI 실행 파일이
그 밖에 별도로 필요**하다. 이건
PyPI wheel 안에 들어있지 않으므로 별도로 챙겨야 한다.

- Node.js LTS 바이너리(tar.gz 또는 사내 표준 배포판)
- `claude` CLI: `npm pack`으로 인터넷 환경에서 tarball을 받아두거나,
  사내 npm 미러에 이미 올라가 있는지 확인
- 폐쇄망에서 `claude` 실행 파일이 PATH에 없다면 `.env`의
  `CLAUDE_CLI_PATH`로 절대경로를 지정하면 되므로, 설치 위치는 자유롭게
  정해도 된다.

> **주의**: 사내 LLM 정책상 Claude Agent SDK(Anthropic CLI 기반) 자체를 폐쇄망에
> 반입할 수 없는 경우, `LLM_PROVIDER=openrouter`로 바꿔도 `claude-agent-sdk`
> 패키지와 `claude` CLI 의존성 자체는 없어지지 않는다 (OpenRouter는 API
> 엔드포인트만 바꾸는 것이지 SDK를 대체하는 게 아니다). 이 경우 Agent 실행
> 계층 자체를 다른 방식으로 교체해야 하며, 그건 이 문서의 범위를 벗어난다 —
> 먼저 사내 LLM 반입 정책을 확인한다.

### Frontend 의존성

프론트엔드는 별도로 [frontend/docs/closed-network.md](../../frontend/docs/closed-network.md)의
원칙을 따른다. npm 패키지는 순수 npm 의존성만 쓰도록 이미 검증돼 있으므로,
`npm install` 실행 후 나온 `node_modules`를 통째로 옮기거나 사내 npm
레지스트리에 미러링한다. shadcn/AI Elements 컴포넌트는 이미 소스로 커밋되어
있어 CLI 실행이 폐쇄망에서 필요 없다.

## 1-2. 폐쇄망 PC로 이전

- 소스 코드, `offline-packages/` 디렉토리, Node.js/`claude` CLI 바이너리,
  (필요 시) `node_modules`를 반입 절차(사내 보안 검토 포함)에 따라 옮긴다.
- `.env`, `.env.local`, API 키, DB 비밀번호 등 **민감정보는 코드와 별도
  채널로 옮긴다** — 소스 코드 저장소나 이 오프라인 패키지 번들에 포함하지
  않는다.

## 1-3. 폐쇄망에서 Python 환경 구성

```bash
cd backend
conda env create -f environment.yml     # 최초 1회 (Python 3.11)
conda activate production-planning

# PyPI 접근이 안 되므로 오프라인 번들에서 설치
pip install --no-index --find-links=./offline-packages -r requirements-dev.txt
```

- 사내 PyPI 미러가 있다면 `--index-url http://<사내미러>/simple`로 대체하고
  `--no-index --find-links`는 생략한다.
- `pip install` 로그에서 실패한 패키지가 있으면 1-1에서 해당 wheel이
  빠졌거나 플랫폼이 안 맞는 것이다 — 인터넷 환경에서 다시 받아온다.

## 1-4. 폐쇄망에서 Claude CLI 구성

```bash
# Node.js 설치 (사내 배포 방식에 따라 tar.gz 압축 해제 또는 패키지 설치)
# claude CLI 설치 (npm pack 받은 tarball을 npm install -g ./claude-*.tgz 등으로)
which claude   # PATH에 잡히는지 확인
```

- PATH에 안 잡히면 `.env`의 `CLAUDE_CLI_PATH=/절대/경로/claude`로 지정한다
  (`backend/core/config.py`가 `CLAUDE_CLI_PATH → PATH → SDK 자체 탐색` 순으로
  찾는다).

## 1-5. `.env` 구성

```bash
cp .env.example .env
```

최소한 아래를 채워야 서버가 정상 기동한다:

| 키                                                | 값                                                | 비고                                                                                                                                                    |
| ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SERVICE_MODE`                                  | `mock` (최초 검증) → `real` (Part 2 완료 후) | Part 2 참고                                                                                                                                             |
| `LLM_PROVIDER`                                  | `anthropic` 또는 `openrouter`                 | 사내 LLM 반입 정책에 따름                                                                                                                               |
| `ANTHROPIC_API_KEY` 또는 `OPENROUTER_API_KEY` | 사내 발급 값                                      | 폐쇄망에서 실제 외부 API 호출이 안 되면 사내 LLM 게이트웨이 주소로 대체 필요 — 이 경우`core/config.py`의 `agent_provider_env()` 수정이 별도로 필요 |
| `CLAUDE_CLI_PATH`                               | PATH에 없을 때만                                  | 1-4 참고                                                                                                                                                |

`real` 서비스 관련 환경변수(DB/Milvus/Simulation MCP 접속 정보)는
`SERVICE_MODE=real` 전환 시점에 Part 2 §2-3을 따라 추가한다.

## 1-6. 기동 및 검증

```bash
uvicorn main:app --reload --port 8000
curl http://localhost:8000/health   # {"status":"ok"}
```

먼저 `SERVICE_MODE=mock`, `PLANNING_AGENT_FAKE=1`로 Claude 호출 없이 이벤트
흐름만 검증한다 (`backend/README.md` "Agent 실행 모드" 참고):

```bash
PLANNING_AGENT_FAKE=1 uvicorn main:app --port 8000
curl -N -X POST localhost:8000/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"9월에 A라인에서 1000개 생산 가능한가?","conversation_id":"c1"}'
```

이게 통과하면 `PLANNING_AGENT_FAKE=0`으로 바꿔 실제 Claude Agent SDK
경로(1-4의 CLI, 1-5의 API 키)를 검증한다. 그 다음에야 Part 2(`SERVICE_MODE=real`
전환, pntfp 로직 이식)로 넘어간다.

## 1-7. 자주 막히는 지점 체크리스트

- [ ] `pip install`이 특정 패키지에서 "no matching distribution" → 1-1
  플랫폼/파이썬 버전 재확인
- [ ] `claude` CLI 실행 시 `CLINotFoundError` → PATH 또는 `CLAUDE_CLI_PATH`
  확인 (1-4)
- [ ] 서버는 뜨는데 `/api/chat` 호출 시 인증 오류 → `ANTHROPIC_API_KEY`/
  `OPENROUTER_API_KEY`가 폐쇄망에서 실제로 도달 가능한 엔드포인트를
  가리키는지 확인 (사내 LLM 게이트웨이 사용 시 `agent_provider_env()`
  커스터마이징 필요할 수 있음)
- [ ] `SERVICE_MODE=real`로 바꿨더니 `NotImplementedError` →
  Part 2의 이식 작업이 아직 안 끝난 것 — mock으로 되돌려 프론트/에이전트
  흐름부터 격리 확인
- [ ] 프론트 연동 시 CORS 오류 → `backend/core/config.py`의
  `CORS_ALLOW_ORIGINS`에 폐쇄망 프론트 도메인 추가

---

# Part 2. pntfp 서비스 로직 이식

`pntfp` 폴더(기존 프로젝트)의 실제 서비스 로직과 설정값을, 이 저장소의
`SERVICE_MODE=real` 구현체로 이식한다. **Part 1을 마쳐 폐쇄망 PC에서
`SERVICE_MODE=mock`으로 서버가 정상 기동하는 상태를 전제**로 한다.

Claude Code에게 이 문서 경로를 알려주고 "이 가이드를 보고 이식해줘"라고
지시하면 된다.

## 2-0. 사전 준비 (사람이 확인)

- [ ] `pntfp` 폴더와 `production-planning-agent` 폴더가 같은 PC의 접근
  가능한 경로에 있는지 확인
- [ ] `pntfp/config.dev.yaml` 파일 위치 확인
- [ ] 이 저장소는 `main` 브랜치가 clean한 상태에서 시작 (`git status`)
- [ ] 작업은 새 브랜치에서 진행 (예: `feature/pntfp-real-services`)

## 2-1. 작업 목표

`backend/services/real/` 아래 3개 파일은 현재 자리만 잡힌 스텁이다.
pntfp의 실제 로직을 그대로 옮기되, **아래 함수 시그니처와 반환 스키마는
반드시 그대로 유지**한다. 이 계약이 깨지면 `tools/*.py`, `agent/agent.py`
등 호출부를 전부 수정해야 하므로 절대 바꾸지 않는다.

### `backend/services/real/sql_service.py`

```python
class RealSQLService:
    async def generate_and_query(self, question: str) -> dict:
        ...
```

- pntfp 쪽에서 SQL 생성 + DB 조회를 담당하는 코드를 찾아 이식한다.
  (Text-to-SQL, DB 커넥션, 쿼리 실행 로직 전부 포함)
- 반환값은 mock 구현(`backend/services/mock/mock_sql_service.py`)과
  동일한 키 구조를 유지한다: `status`, `question`, `generated_sql`, `rows`
- DB 접속 정보(호스트/포트/계정/비밀번호)는 코드에 하드코딩하지 않고
  §2-3의 환경변수로 주입한다.
- 모듈 하단의 `_service = RealSQLService()` 인스턴스와
  `generate_and_query(question)` 모듈 함수 래퍼는 그대로 유지한다
  (`services/__init__.py`, `tools/sql_tool.py`가 이 모듈 함수를 그대로 import 한다).

### `backend/services/real/rag_service.py`

```python
class RealRAGService:
    async def search(self, query: str) -> dict:
        ...
```

- pntfp의 Milvus / Hybrid Search 로직을 이식한다.
- 반환값은 mock 구현(`mock_rag_service.py`)과 동일한 키 구조:
  `status`, `query`, `documents`(`title`, `content`, `score`)
- Milvus 접속 정보(host/port/collection 등)는 §2-3의 환경변수로 주입한다.
- 모듈 하단의 `_service = RealRAGService()` 인스턴스와
  `search(query)` 모듈 함수 래퍼는 그대로 유지한다.

### `backend/services/real/simulation_service.py`

```python
class RealSimulationService:
    async def list_simulation(self) -> dict: ...
    async def run_simulation(self, simulation_type: str, params: dict) -> dict: ...
```

- pntfp의 Simulation MCP Server 호출 로직을 이식한다.
- 시뮬레이션 종류는 `knowledge/simulations/*.yaml`과
  `services/simulation_registry.py`를 기준으로
  `run_simulation(simulation_type, params)` 하나의 진입점에서 분기 처리한다.
- 현재 mock의 `SMT2020_입력검증`은 실제 DES가 아니라 입력 관계 검증이다.
  폐쇄망의 실제 simulation 종류는 동일한 YAML registry에 추가한다.
- `run_simulation` 내부에서 `simulation_type`/필수 파라미터 검증은
  이미 `validate_simulation_request()`가 처리하므로 중복 검증하지 않는다.
- 반환 dict 구조는 대응하는 `mock_simulation_service.py`의 Result Store와
  simulation payload 계약을 참고해 맞춘다.
- Simulation MCP 서버 주소/포트는 §2-3의 환경변수로 주입한다.
- 모듈 하단의 `_service = RealSimulationService()` 인스턴스와
  `list_simulation()` / `run_simulation(simulation_type, params)` 모듈 함수
  래퍼는 그대로 유지한다.

### 변경하지 않는 것

- `backend/tools/*.py` — 이미 `services.<name>_service`를 호출하도록
  구성되어 있고, `services/__init__.py`가 `SERVICE_MODE`에 따라
  mock/real을 자동 스위칭한다. 이 파일들은 수정 불필요.
- `backend/agent/*.py` — Agent SDK 실행 로직은 서비스 구현과 무관하다.
- mock 파일들(`backend/services/mock/*.py`) — 삭제하지 않는다.
  `SERVICE_MODE=mock`으로 되돌려 데모/테스트할 때 계속 사용한다.

## 2-2. pntfp 코드 탐색 지시 (Claude Code가 수행)

1. `pntfp` 폴더 구조를 훑어서 다음 3가지 로직이 있는 파일을 찾는다:
   - SQL 생성/DB 조회 관련 코드
   - Milvus / RAG / Hybrid Search 관련 코드
   - Simulation MCP 호출 관련 코드
2. 각 로직이 사용하는 라이브러리(DB 드라이버, Milvus 클라이언트,
   MCP 클라이언트 등)를 확인하고, `backend/requirements.txt`에
   빠진 패키지가 있으면 추가한다.
3. pntfp 쪽 함수 시그니처가 위 §2-1의 시그니처와 다르면, **로직은 재사용하되
   래핑(wrapping)해서** `services/real/*.py`의 시그니처에 맞춘다.
   (pntfp 함수를 그대로 옮기고, 얇은 어댑터 함수로 감싸는 방식을 권장)
4. pntfp에 있는 프롬프트/스키마/상수 등 부수 자료도 필요하면
   `backend/services/real/` 아래에 함께 이식한다
   (예: `backend/services/real/_sql_prompts.py` 같은 보조 모듈).

## 2-3. `config.dev.yaml` → `.env` 매핑

이 프로젝트는 YAML 설정 파일을 쓰지 않고 `.env` + `core/config.py`
방식을 사용한다. `pntfp/config.dev.yaml`의 키들을 아래 규칙으로 옮긴다.

### 작업 절차

1. `pntfp/config.dev.yaml`을 열어 키-값 목록을 정리한다.
2. 아래 카테고리별로 `backend/.env.example`에 **새 키를 추가**한다
   (값은 비워두고 키 이름과 주석만 작성 — 예시 파일이므로 실제 값을 넣지 않는다).
3. `backend/.env` (실제 환경변수 파일, git 미추적)에 실제 값을 채운다.
4. `backend/core/config.py`에 해당 환경변수를 읽어들이는 상수를 추가한다.
   (기존 `ENV`, `SERVICE_MODE` 등과 같은 패턴으로 `os.getenv(...)` 사용)
5. `services/real/*.py`에서는 `core.config`에서 import해서 사용한다.
   (환경변수를 서비스 코드에서 직접 `os.getenv`로 읽지 않는다 — 설정은
   `core/config.py`에 모아두는 기존 패턴을 따른다)

### 카테고리 매핑 가이드

| pntfp config.dev.yaml 영역                         | 이식 위치                                                                                                                         | 비고                                              |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| DB 접속 정보 (host, port, user, password, db name) | `.env`: `SQL_DB_HOST`, `SQL_DB_PORT`, `SQL_DB_USER`, `SQL_DB_PASSWORD`, `SQL_DB_NAME`                                 | 이름은 프로젝트 컨벤션에 맞게 조정 가능           |
| Milvus 접속 정보 (host, port, collection)          | `.env`: `MILVUS_HOST`, `MILVUS_PORT`, `MILVUS_COLLECTION`                                                                 |                                                   |
| Simulation MCP 서버 주소                           | `.env`: `SIMULATION_MCP_URL` (또는 host/port 분리)                                                                            |                                                   |
| LLM 모델/Provider 설정                             | 기존`.env` 키 재사용: `LLM_PROVIDER`, `AGENT_MODEL`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` | 새 키를 만들지 말고 기존 키에 pntfp 값을 채운다   |
| 기타 임계값/상수 (배치 크기, timeout 등)           | `.env`에 새 키 추가하거나, 상수 성격이면 `core/config.py`에 직접 정의                                                         | 자주 안 바뀌는 순수 상수는`.env`로 뺄 필요 없음 |

### 절대 금지

- API 키, DB 비밀번호, 사내 내부 URL 등 민감정보를 `.env.example`,
  코드, 커밋 메시지, 이 문서에 **직접 적지 않는다**. 반드시 `.env`
  파일에만 넣는다 (`.gitignore`에 이미 포함되어 있는지 재확인).
- `config.dev.yaml` 파일 자체를 이 저장소로 복사해오지 않는다.
  (설정 방식을 이원화하지 않기 위함 — 값만 이식하고 형식은 `.env`로 통일)

## 2-4. 이식 후 검증 절차

1. `backend/.env`에서 `SERVICE_MODE=real`로 변경
2. 필요한 신규 환경변수가 모두 채워졌는지 확인
3. 백엔드 기동:

```bash
cd backend
source venv/bin/activate  # 가상환경 사용 시
uvicorn main:app --reload --port 8000
```

4. `curl http://localhost:8000/health` → `{"status":"ok"}` 확인
5. 프론트엔드(`npm run dev`)에서 실제 채팅으로 다음 3가지 질의를 각각
   테스트해서 real 서비스가 정상 호출되는지 확인:
   - SQL 조회가 필요한 질문 (예: 생산 실적 조회)
   - RAG 검색이 필요한 질문 (예: 공정 매뉴얼 질의)
   - Simulation이 필요한 질문 (등록된 실제 simulation type 사용)
6. 문제 발생 시 `SERVICE_MODE=mock`으로 되돌려 프론트/에이전트 흐름
   자체는 정상인지 먼저 격리해서 확인한다.

## 2-5. 커밋 시 주의사항

- `.env` 파일은 절대 커밋하지 않는다 (`.gitignore` 확인).
- `__pycache__`, `.pyc` 파일이 스테이징되지 않도록 확인한다.
- 커밋 전 `git status`로 의도치 않은 파일(사내 자료, 인증정보 등)이
  포함되지 않았는지 반드시 확인한다.
