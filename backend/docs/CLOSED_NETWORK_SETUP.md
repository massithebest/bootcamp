# 폐쇄망 배포 & pntfp 이식 가이드

이 문서는 **Windows 폐쇄망 PC로 코드를 이전해 백엔드를 기동하고, 최종적으로
pntfp의 실제 서비스 로직(SQL/RAG/Simulation)을 이식하기까지**의 절차를 두
단계로 정리한다. Python 패키지는 폐쇄망에서 접근 가능한 사내 Nexus를 통해
설치하는 환경을 전제로 한다.

```text
Part 1. 폐쇄망 인프라 구축        Part 2. pntfp 서비스 로직 이식·검증
  소스 코드 반입 → .venv 구성        services/production/* 스텁을 실제 로직으로 교체
  → Nexus 의존성 설치               → 운영 지식 반입 → prod/production 설정
                                      → 공통 테스트 → production 관통 검증
```

합성 mock DB·문서 생성기가 만든 산출물(`backend/data/` 하위)과
`backend/knowledge/mock/` YAML은 개발용 자산이며 폐쇄망 운영 지식으로 반입하지 않는다.
실제 YAML은 `backend/knowledge/production/`에 추가해 반입한다(또는 같은 내용의 별도
영속 디렉터리를 사용한다). 폐쇄망 서버는 `ENV=prod`, `SERVICE_MODE=production`, 명시적인
운영 `KNOWLEDGE_DIR`이 모두 준비된 뒤에만 기동한다. Part 2는 Claude Code에게 이 문서
경로를 알려주고 "이 가이드를 보고 이식해줘"라고 지시하는 방식으로 실행하면 된다.

---

# Part 1. 폐쇄망 인프라 구축

## 1-0. 전체 흐름

```text
[코드 준비 환경]                      [Windows 폐쇄망 환경]
1. 소스 코드 확보                  →  2. 소스 코드 반입
                                      3. .venv 생성 및 활성화
                                      4. 사내 Nexus에서 의존성 설치
                                      5. production 서비스·운영 지식 반입 준비
```

폐쇄망 PC는 인터넷 PyPI 대신 기존 사내 Nexus를 사용한다. 별도의 wheel 번들을
만들거나 반입하지 않는다.

## 1-1. 인터넷 환경에서 준비할 것

### 소스 코드

- 이 저장소(`production-planning-agent`) 전체를 클론/압축한다.
- `.git` 히스토리가 필요 없다면 변경을 커밋한 뒤 `git archive HEAD`로
  커밋된 파일만 내보낼 수 있다. `git archive`에는 미커밋·미추적 파일이
  포함되지 않으므로 반입 전 `git status --short`로 누락 여부를 확인한다.
  히스토리가 필요하면 `.git` 폴더까지 통째로 옮긴다.
- `.venv`, `__pycache__` 등 로컬 환경과 캐시는 제외한다. 가상환경은 폐쇄망
  PC에서 다시 만든다.
- `backend/data/`에 생성된 합성 mock SQLite(`mock_planning.db`,
  `knowledge.sqlite3`)는 개발용 산출물이므로 반입물에서 제외한다.
  `backend/scripts/`는 실제 데이터를 다루지 않는 순수 코드이므로 반입해도
  무방하다.

### Python 의존성 확인

- `requirements.txt`가 포함하는 각 패키지가 **사내에서 사용 가능한 이름/버전인지
  Nexus에 등록되어 있는지 사전 확인**한다. 특히 아래는 원래 pntfp 환경
  기준으로 들어간 항목이라 폐쇄망 사내 표준과 다를 수 있다. 다르면 실제
  이식 시(Part 2) 맞춰 교체한다:
  - `langchain`, `langchain-openai` (LLM 연동 방식이 사내 표준과 다르면 교체)
  - `pymilvus` (사내 Milvus 서버 버전과 클라이언트 버전이 맞아야 함)
  - `httpx` (폐쇄망에서 반입할 HTTP 연동 코드의 의존성으로 사용 예정)

## 1-2. 폐쇄망 PC로 이전

- 소스 코드를 반입 절차(사내 보안 검토 포함)에 따라 옮긴다.
- `.env`, `.env.local`, API 키, DB 비밀번호 등 **민감정보는 코드와 별도
  채널로 옮긴다**. 소스 코드 저장소에 포함하지 않는다.

## 1-3. 폐쇄망에서 Python 환경 구성

Windows PowerShell에서 `backend` 폴더로 이동한 뒤 Python 3.11 기반 `.venv`를
만들어 활성화한다.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

사내 Nexus가 pip 기본 인덱스로 설정되어 있지 않다면 보안 담당자가 제공한
저장소 주소를 명시한다.

```powershell
python -m pip install `
  --index-url "https://<사내-Nexus-주소>/repository/<PyPI-저장소>/simple" `
  -r requirements.txt
```

- 설치가 실패하면 Python 3.11용 패키지와 전이 의존성이 Nexus에 모두
  등록되어 있는지 확인한다.
- PowerShell 실행 정책으로 활성화 스크립트를 실행할 수 없으면 사내 보안
  정책에 맞는 실행 정책을 적용하거나 `.venv\Scripts\python.exe`를 직접 사용한다.

## 1-4. 운영 설정 준비

```powershell
Copy-Item .env.example .env
```

실제 값은 Part 2의 production 서비스 이식과 운영 지식 반입을 마친 뒤 채운다. 서버를
먼저 mock으로 기동하지 않는다. 최소 운영 계약은 다음과 같다.

| 키 | 값 | 비고 |
| --- | --- | --- |
| `ENV` | `prod` | 폐쇄망 운영 모드 |
| `SERVICE_MODE` | `production` | 기존 `real` 값도 호환 별칭으로 허용 |
| `BACKEND_PORT` | 실제 기동 포트(예: `8100`) | `uvicorn --port`와 반드시 일치. `LLM_PROVIDER=local`의 `/anthropic` 자기 참조 URL에 쓰임 |
| `API_TIMEOUT_SECONDS` | `60`(기본) | 폐쇄망 production API 요청 timeout(초). 실제 SQL/RAG/simulation API adapter가 연결되면 이 값을 사용 |
| `KNOWLEDGE_DIR` | 운영 YAML의 별도 절대경로 | bundled mock 지식 경로는 허용하지 않음 |
| `LLM_PROVIDER` | 사내 지원 provider | 사내 LLM 반입 정책에 따름 |
| provider 인증값 | 사내 발급 값 | 코드·문서·로그에 기록하지 않음 |
| `KNOWLEDGE_DB_PATH` | 영속 볼륨의 SQLite 경로 | 텍스트 지식 저장소. 비우면 `backend/data/knowledge.sqlite3` |
| `KNOWLEDGE_SEARCH_BACKEND` | `local`(기본) 또는 `service` | `service`는 사내 RAG 어댑터(`services/production/rag_service.py`) 구현 후에만 사용 |
| `CORS_ALLOW_ORIGINS` | 실제 Frontend Origin | 기본값은 localhost 개발 Origin |
| `KNOWLEDGE_MANAGEMENT_ENABLED` | `true`(기본) 또는 `false` | `false`면 구조화 지식 변경 요청의 쓰기를 막고 조회만 허용. 현재 `X-User-Id` 권한 스텁은 인증이 아니므로 실제 사용자에게 쓰기를 열기 전에 인증을 연결하거나 접근을 제한 |
| `KNOWLEDGE_PRINCIPALS` | `{id: {name, permissions[]}}` JSON | 인증 체계 전 스텁. 비우면 사용자(작성)·관리자(작성+승인) 기본값 |
| `KNOWLEDGE_ALLOW_SELF_APPROVAL` | `false`(기본) | 작성자 본인 승인을 허용할 때만 `true` |

`production` 서비스 관련 환경변수(DB/Milvus/Simulation API 접속 정보)는
Part 2 §2-3을 따라 추가한다. `MOCK_DB_PATH`는 설정하지 않는다.
`API_TIMEOUT_SECONDS`는 공통 timeout 설정으로 미리 제공하며, 현재 production
서비스는 외부 API 호출을 구현하지 않아 아직 이 값을 사용하지 않는다.

### `LLM_PROVIDER=local`과 `/anthropic` 프록시

사내 LLM 게이트웨이(HCP)가 Claude CLI의 User-Agent를 차단해 직접 연결할 수 없을
때 사용한다. 이 저장소에는 `/anthropic` 경로와 `LLM_PROVIDER=local` 분기만 준비돼
있다. 프록시 본문은 의도적으로 비워 둔 상태이며, 폐쇄망에서 동작 가능한 구현을
반입한 뒤 `backend/api/routes_anthropic_proxy.py`에 채워야 한다. 반입 전 이 경로는
501을 반환하므로 `LLM_PROVIDER=local`로는 Agent 요청이 동작하지 않는다.

```dotenv
LLM_PROVIDER=local
BACKEND_PORT=8100
PRIVATE_LLM_MODEL_NAME=
PRIVATE_LLM_MODEL_ENDPOINT=
PRIVATE_LLM_MODEL_KEY=
```

- `BACKEND_PORT`는 `uvicorn main:app --port <값>`의 포트와 반드시 같아야 한다.
  CLI가 자기 자신(`http://127.0.0.1:<BACKEND_PORT>/anthropic`)으로 요청을 보내기
  때문이다.
- `PRIVATE_LLM_MODEL_ENDPOINT`와 `PRIVATE_LLM_MODEL_KEY`는 기존 설정 예시로
  남아 있다. 반입할 구현의 실제 환경변수·인증 규칙에 맞춰 필요 여부와 사용법을
  확인한다.

## 1-5. 기동 전 확인

- [ ] 합성 mock DB/문서 생성기의 산출물(`backend/data/`)이 반입물에 없는지 확인
- [ ] `requirements.txt` 설치가 완료됐는지 확인
- [ ] production 서비스 원본과 운영 지식이 승인된 별도 경로에 준비됐는지 확인
- [ ] 텍스트 지식 SQLite(`KNOWLEDGE_DB_PATH`)가 백업되는 영속 볼륨을 가리키는지 확인.
  `services/knowledge/documents.py`는 앱 import 경로에 포함되므로 코드는 반드시 반입하고,
  DB는 비어 있어도 첫 접근 때 스키마를 만든다
- [ ] 구조화 지식 변경 요청을 쓰려면 `KNOWLEDGE_DIR`가 서비스 계정에 쓰기 가능한지,
  백엔드가 uvicorn 단일 워커인지, `KNOWLEDGE_DIR`와 `KNOWLEDGE_DB_PATH`가 함께 백업되는지 확인
- [ ] Part 2 완료 전에는 백엔드를 기동하지 않음

## 1-6. 자주 막히는 지점 체크리스트

- [ ] `pip install`이 특정 패키지에서 "no matching distribution" → Python
  버전과 Nexus의 해당 패키지·전이 의존성 등록 여부 확인
- [ ] 서버는 뜨는데 `/api/chat` 호출 시 인증 오류 → `ANTHROPIC_API_KEY`/
  `OPENROUTER_API_KEY`가 폐쇄망에서 실제로 도달 가능한 엔드포인트를
  가리키는지 확인. 사내 LLM 게이트웨이가 CLI User-Agent를 차단하면
  `LLM_PROVIDER=local`과 `/anthropic` 프록시를 쓴다(위 "`LLM_PROVIDER=local`과
  `/anthropic` 프록시" 참고)
- [ ] production Tool 호출에서 `NotImplementedError` → Part 2의 이식 작업이 아직
  끝나지 않은 것. mock으로 우회하지 말고 해당 production adapter 구현을 완료
- [ ] 시작 시 `ENV=prod requires ...` 오류 → `SERVICE_MODE=production`과 별도 운영
  `KNOWLEDGE_DIR` 설정 및 디렉터리 존재 여부 확인
- [ ] 프론트 연동 시 CORS 오류 → `backend/core/config.py`의
  `CORS_ALLOW_ORIGINS`에 폐쇄망 프론트 도메인 추가

---

# Part 2. pntfp 서비스 로직 이식

이식에 필요한 파일을 `backend/pntfp/`에 임시로 반입한 뒤, 파일명을 기준으로
현재 프로젝트의 대상 파일에 병합한다. `backend/pntfp/`에는 하위 폴더를 만들지
않고 모든 파일을 한 단계에 둔다. **Part 1의 환경 구성과 반입 검토가 끝났으며,
아직 서버를 기동하지 않은 상태**를 전제로 한다.

Claude Code에게 이 문서 경로를 알려주고 "이 가이드를 보고 이식해줘"라고
지시하면 된다.

## 2-0. 반입 폴더와 사전 확인

- [ ] `backend/pntfp/`가 하위 폴더 없이 아래 파일들로만 구성되어 있는지 확인
- [ ] 실제 비밀값이 포함될 수 있는 `backend/pntfp/.env`의 접근 권한과 반입·보관
  정책 확인
- [ ] `backend/pntfp/`가 Git에 포함되지 않도록 `.gitignore`에 등록되어 있는지 확인
- [ ] `backend/.env`와 `backend/pntfp/.env`가 모두 Git 추적 대상이 아닌지 확인
- [ ] 이 저장소는 `main` 브랜치가 clean한 상태에서 시작 (`git status`)
- [ ] 작업은 새 브랜치에서 진행 (예: `feature/pntfp-production-services`)

예상 반입 파일은 다음과 같다.

```text
backend/pntfp/
  .env
  CLAUDE.md
  common_sql_client.py
  config.py
  milvus_client.py
  rag_service.py
  simulation_service.py
  sql_prompts.py
  sql_service.py
  sumulation_api_client.py
  system_prompt.py
```

`sumulation_api_client.py`는 반입 파일의 제공된 철자를 그대로 적은 것이다.
이식할 때 대상 파일명은 `simulation_api_client.py`로 바로잡고, 이 파일을
참조하는 import도 함께 수정한다. 실제 반입 파일명이 이미
`simulation_api_client.py`라면 그 이름을 그대로 사용한다.

예상 목록에 없는 파일이나 같은 역할의 중복 파일이 있으면 임의로 복사하지 말고,
import 관계와 사용처를 확인한 뒤 대상과 필요성을 먼저 결정한다.

## 2-1. 파일명 기준 매핑

반입 파일로 대상 파일을 통째로 덮어쓰지 않는다. 양쪽 파일을 읽고 현재 프로젝트의
공개 함수, 보안 가드레일, Result Store와 mock/production 계약을 보존하면서 필요한
구현만 병합한다.

| 반입 파일 | 대상 | 처리 방식 |
| --- | --- | --- |
| `.env` | `backend/.env` | 양쪽 파일의 키를 비교해 필요한 설정만 키 단위로 병합한다. 대상 파일 전체를 덮어쓰거나 실제 값을 `.env.example`에 복사하지 않는다. |
| `system_prompt.py` | `backend/agent/system_prompt.py` | production service에 맞게 수정된 역할·응답 규칙을 병합하되 `SYSTEM_PROMPT` 공개 이름과 현재 금지사항을 유지한다. |
| `CLAUDE.md` | `backend/agent/agent_sdk/CLAUDE.md` | production service용 Tool 사용 순서와 지식 조회 규칙을 병합한다. 등록 Tool 이름과 일치해야 한다. |
| `config.py` | `backend/core/config.py` | 기존 설정을 유지하고 `local` provider 및 현재 파일에 없는 설정만 추가한다. `LLM_PROVIDER=local`, `PRIVATE_LLM_*`, production 어댑터 env var 자리는 이미 준비돼 있다. |
| `milvus_client.py` | `backend/services/production/milvus_client.py` | 이미 `get_embedding_function`, `get_milvus_client` 가드레일 스텁이 있다. 새로 만들지 않고 `NotImplementedError` 부분에 실제 로직만 채운다. |
| `common_sql_client.py` | `backend/services/production/common_sql_client.py` | 이미 `CommonSqlClient` 가드레일 스텁이 있다. 새로 만들지 않고 `execute()`의 `NotImplementedError` 부분에 DB 연결·실행 로직만 채운다. |
| `rag_service.py` | `backend/services/production/rag_service.py` | 기존 `search(query)` 계약을 유지하면서 실제 Milvus/RAG 구현을 병합한다. |
| `sumulation_api_client.py` | `backend/services/production/simulation_api_client.py` | 이미 `SimulationApiClient` 가드레일 스텁이 있다(파일명은 이미 `simulation_api_client.py`로 맞춰져 있음). 새로 만들지 않고 `run()`의 `NotImplementedError` 부분에 실제 Simulation API 호출만 채운다. |
| `simulation_service.py` | `backend/services/production/simulation_service.py` | 기존 simulation registry, 입력 검증, `access_scope`와 반환 계약을 유지하면서 구현을 병합한다. |
| `sql_service.py` | `backend/services/production/sql_service.py` | Text-to-SQL 생성은 옮기지 않고, Agent가 전달한 SQL의 읽기 전용 실행 구현만 병합한다. |
| `sql_prompts.py` | 기본적으로 직접 복사하지 않음 | 기존 Text-to-SQL 프롬프트에서 테이블·조인·KPI·업무 규칙을 추출해 별도 운영 `KNOWLEDGE_DIR`에 반영한다. 런타임 SQL 생성 프롬프트로 연결하지 않는다. |

`backend/services/mock/`, `backend/tools/`, `backend/agent/agent.py`는 반입 파일로
교체하지 않는다. 호출 계약을 맞추는 데 꼭 필요한 변경이 있으면 호출자와 테스트를
함께 확인해 최소 범위로 수정한다.

## 2-2. 병합 순서

1. 반입 파일 목록과 각 파일의 import, 환경변수, 외부 패키지, 공개 함수 목록을
   정리한다.
2. 반입 `.env`와 `config.py`의 키 목록을 대조한다. 신규 설정 정의는
   `backend/core/config.py`와 `.env.example`에 추가하고, 실제 값은
   `backend/.env`에만 키 단위로 병합한다.
3. `milvus_client.py`, `common_sql_client.py`, `simulation_api_client.py` 보조
   모듈을 추가하고 import를 현재 패키지 경로에 맞춘다.
4. SQL, RAG, simulation 서비스 구현을 기존 `services/production` 계약에 맞춰
   병합한다.
5. `system_prompt.py`와 `CLAUDE.md`의 production service 지침을 현재 Agent Tool 계약에
   맞춰 병합한다.
6. 서비스와 기존 SQL 프롬프트에서 확인한 도메인 정보를
   `backend/knowledge/production/` YAML에 반영한다. 디렉터리 구조는 mock과 같게
   `catalog/`, `kpi/`, `recipes/`, `simulations/`, `scenarios/`, `glossary.yaml`로
   만들고, 실제 운영 환경변수 `KNOWLEDGE_DIR`는 이 디렉터리의 절대경로로 지정한다.
   운영 YAML을 별도 영속 볼륨에 둘 때도 동일한 구조를 복사하고 그 경로를 지정한다.
7. 신규 import에 필요한 패키지만 `backend/requirements.txt`에 추가하고 사내
   Nexus에 해당 버전과 전이 의존성이 있는지 확인한다.
8. 계약 테스트와 전체 백엔드 테스트를 실행한 뒤 `SERVICE_MODE=production` 관통 검증을
   수행한다.

병합이 끝난 뒤 런타임 코드가 `backend/pntfp/`를 import하면 안 된다. 모든 필요한
구현은 정식 대상 경로에 반영되어야 하며, 반입 폴더를 제거해도 실행되어야 한다.

## 2-3. 설정 병합

반입된 `config.py`로 `backend/core/config.py`를 덮어쓰지 않는다. 현재 파일의
`ENV`, `SERVICE_MODE`, 저장소 경로, CORS, 세션, Result Store, 기존 provider
설정을 보존한 뒤 없는 값만 추가한다.

`backend/pntfp/.env`도 `backend/.env` 위에 통째로 복사하지 않는다. 다음 순서로
키 단위 병합을 수행한다.

1. 두 `.env` 파일의 키 이름만 비교한다. 명령 출력, 작업 기록과 대화에는 값을
   표시하지 않는다.
2. 현재 `backend/.env`에 이미 있는 키는 기존 값을 유지하고, 변경이 필요한지는
   반입 설정의 사용처를 확인해 결정한다.
3. 현재 파일에 없는 production service용 키만 `backend/.env`에 추가한다.
4. 코드에서 읽는 모든 신규 키를 `backend/.env.example`에도 빈 값과 설명으로
   추가한다.
5. 반입 `.env`에만 있고 코드에서 사용하지 않는 키는 그대로 복사하지 말고,
   서비스 import와 참조 위치를 확인한 뒤 필요 여부를 결정한다.

`LLM_PROVIDER == "local"` 분기와 `/anthropic` 경로는 준비돼 있다. 프록시 전달 본문은
의도적으로 비워져 있으므로, 폐쇄망 구현 반입 후 채운 다음 `.env` 값을 설정한다.

```dotenv
LLM_PROVIDER=local
BACKEND_PORT=8100
PRIVATE_LLM_MODEL_NAME=
PRIVATE_LLM_MODEL_ENDPOINT=
PRIVATE_LLM_MODEL_KEY=
```

- `backend/.env.example`에는 키와 설명만 있고 실제 모델명, endpoint와 key는
  없다. 값은 Git에서 제외된 `backend/.env`에만 기록한다.
- `PRIVATE_LLM_MODEL_ENDPOINT`가 실제로는 `/v1` 같은 경로 접두어를 포함해야
  한다면(게이트웨이 응답으로 확인), `routes_anthropic_proxy.py`의 URL 조합
  로직을 함께 확인한다.
- 모델 선택이 `AGENT_MODEL`과 별도라면 `AGENT_MODEL`이 비어 있을 때
  `PRIVATE_LLM_MODEL_NAME`으로 폴백하는 `core/config.py`의 동작이 실제
  게이트웨이 모델명과 맞는지 확인한다.
- 반입 `config.py`에 DB, Milvus, Simulation API 관련 설정이 더 있으면 이미
  추가된 `COMMON_SQL_API_URL`/`SIMULATION_API_URL`/`MILVUS_*`/
  `IFLOW_EMBEDDING_*`/`RERANKER_*`/`RAG_DOC_URL_BASE`와 중복 여부를 먼저
  확인하고, 없는 설정만 같은 방식으로 추가한다.
- 신규 설정은 빈 값일 때의 동작과 필수 여부를 명시하고, 시작 시 또는 실제
  service 호출 시 이해 가능한 오류를 내도록 한다. 비밀값 자체는 로그에 남기지
  않는다.

## 2-4. 서비스별 이식 계약

### `backend/services/production/sql_service.py`

```python
class ProductionSQLService:
    async def execute_sql(
        self, sql: str, purpose: str, *, access_scope: str | None = None
    ) -> dict:
        ...
```

- SQL은 Agent SDK가 `list_tables`, `describe_table`, KPI와 recipe 등
  운영 `KNOWLEDGE_DIR`의 정보를 조회해 직접 생성한다. production SQL service는 자연어 질문을
  받아 SQL을 생성하지 않고, 전달받은 SQL을 실행하는 역할만 한다.
- 반입 `sql_service.py`와 `sql_prompts.py`에 남아 있는 기존 Text-to-SQL 호출,
  LLM prompt 조합과 `generate_and_query(question)` 경로는 이식하지 않는다.
- DB 연결과 실제 조회는 `common_sql_client.py`를 사용하되, 실행 전 반드시
  `services/sql/guard.py::check_sql`과 catalog 허용 테이블 검사를 통과시킨다.
  현재 정규식 가드는 인용된 식별자의 미등록 테이블 참조를 놓칠 수 있다.
  이식 시 SQL 파서 또는 DB의 실제 참조 테이블 검증을 추가하고, DB 계정도
  허용 테이블만 읽을 수 있게 제한한다.
- 반환값과 Result Store 저장 방식은
  `backend/services/mock/mock_sql_service.py`와 동일하게 유지한다. 성공한
  Tool 응답은 `status`, `kind`, `purpose`, `result_id`, `row_count`,
  `source_truncated`, `columns`, 최대 5건의 `sample_rows`와 요약 통계만 담는다.
  전체 행과 접근 scope는 Tool 응답에 넣지 않고 Result Store에 저장한다.
- 모듈 하단의 `_service = ProductionSQLService()` 인스턴스와
  `execute_sql(sql, purpose, *, access_scope=None)` 모듈 함수 래퍼를 유지한다.
- DB 접속 정보는 `core.config`에서 import하며 코드에 하드코딩하지 않는다.

### `backend/services/production/rag_service.py`

```python
class ProductionRAGService:
    async def search(self, query: str) -> dict:
        ...
```

- `milvus_client.py`의 `get_embedding_function`, `get_milvus_client`를 사용해
  pntfp의 Milvus / Hybrid Search 로직을 이식한다.
- 반환값은 mock 구현(`mock_rag_service.py`)과 동일한 키 구조:
  `status`, `query`, `documents`(`title`, `content`, `score`)
- Milvus와 embedding 설정은 `core.config`에서 가져오고, 연결 객체의 생성·재사용·
  종료 방식과 검색 실패 시 오류 payload를 명확히 한다.
- 모듈 하단의 `_service = ProductionRAGService()` 인스턴스와
  `search(query)` 모듈 함수 래퍼는 그대로 유지한다.

### `backend/services/production/simulation_service.py`

```python
class ProductionSimulationService:
    async def list_simulation(self) -> dict: ...
    async def run_simulation(
        self,
        simulation_type: str,
        params: dict,
        *,
        access_scope: str | None = None,
    ) -> dict: ...
```

- `simulation_api_client.py`를 통해 실제 Simulation API를 호출하도록 이식한다.
- 시뮬레이션 종류는 운영 `KNOWLEDGE_DIR/simulations/*.yaml`과
  `services/simulation/registry.py`를 기준으로
  `run_simulation(simulation_type, params)` 하나의 진입점에서 분기 처리한다.
- 현재 mock의 `입력_정합성_검증`은 개발 전용이며 실제 DES가 아니다.
  폐쇄망의 실제 simulation 종류는 운영 YAML registry에 별도로 정의한다.
- `run_simulation` 내부에서 `simulation_type`/필수 파라미터 검증은
  이미 `validate_simulation_request()`가 처리하므로 중복 검증하지 않는다.
- 반환 dict 구조는 대응하는 `mock_simulation_service.py`의 Result Store와
  simulation payload 계약을 참고해 맞춘다.
- Simulation API 주소와 인증 정보는 `core.config`에서 주입한다.
- 모듈 하단의 `_service = ProductionSimulationService()` 인스턴스와
  `list_simulation()` / `run_simulation(simulation_type, params, *,
  access_scope=None)` 모듈 함수 래퍼를 그대로 유지한다.

## 2-5. 서비스 기준 운영 지식 갱신

Agent가 SQL을 올바르게 생성하려면 실제 DB와 서비스에 맞는 구조화 지식이 먼저
갱신되어야 한다. 반입 코드를 실행 가능하게 만드는 것만으로 이식을 완료한 것으로
보지 않는다.

| 확인할 반입 파일 | 추출할 정보 | 반영 위치 |
| --- | --- | --- |
| `common_sql_client.py`, `sql_service.py`, `sql_prompts.py` | 실제 테이블·컬럼·타입·코드값·PK 성격·시간 컬럼·허용 join·grain·주의사항 | 운영 `KNOWLEDGE_DIR/catalog/` |
| `sql_prompts.py`, `sql_service.py` | KPI 정의·공식·단위·기준·집계 규칙과 재사용 가능한 SQL/CTE | 운영 `KNOWLEDGE_DIR/kpi/`, `recipes/` |
| SQL/RAG 코드와 prompt의 업무 용어 | 용어, 동의어, 관련 KPI·테이블 | 운영 `KNOWLEDGE_DIR/glossary.yaml` |
| `simulation_service.py`, `simulation_api_client.py` | simulation type, 별칭, 사용 시점, 필수 파라미터, 출력 스키마, 선후 관계 | 운영 `KNOWLEDGE_DIR/simulations/` |
| 서비스의 대표 업무 흐름 | 검증 질문, recipe/simulation 순서와 기대 결과 | 운영 `KNOWLEDGE_DIR/scenarios/` |

갱신할 때 다음 원칙을 지킨다.

- bundled mock 지식 정의는 개발용 mock 회귀를 위해 그대로 두되 운영
  `KNOWLEDGE_DIR`에 복사하지 않는다.
- SQL 프롬프트에 있던 스키마 설명과 업무 규칙을 런타임 prompt에 중복해서
  유지하지 않는다. 구조화 가능한 내용은 운영 `KNOWLEDGE_DIR`의 YAML을 단일
  기준으로 삼는다.
- SQL 실행 허용 테이블은 catalog에서 결정되므로, 실제 조회 대상 테이블을 빠짐없이
  등록하고 쓰기 대상·시스템 테이블은 등록하지 않는다.
- join cardinality, 원천 grain, 집계 전후 단위, NULL 처리와 시간 기준을 실제
  코드 및 DB 스키마와 대조한다.
- RAG에 남길 매뉴얼·정책 같은 비정형 문서와 catalog/KPI/recipe로 옮길 구조화
  지식을 구분한다.
- 확인되지 않은 내용은 `status: draft`로 추가한다. 담당자가 실제 스키마와 업무
  정의를 검토하고 근거·담당자·갱신일을 기록한 경우에만 `verified`로 바꾼다.
- 기존 `KnowledgeStore` 모델로 표현할 수 없는 필드가 꼭 필요할 때만
  `services/knowledge/catalog.py`, 관련 Tool payload와 테스트를 함께 변경한다.
- Agent 지침의 Tool 이름과 실행 순서는 `backend/agent/sdk_tools.py`,
  `backend/agent/agent_sdk/CLAUDE.md`, `.claude/skills/` 및 knowledge 내용이 서로
  일치하도록 확인한다.

세부 작성 규칙은
[도메인 지식 관리 지침](DOMAIN-KNOWLEDGE-MANAGEMENT.md)을 따른다.

## 2-6. 이식 후 검증 절차

1. `backend/pntfp/`를 제외한 변경 파일에 비밀값과 사내 URL이 들어가지 않았는지
   확인한다.
2. `backend/.env`에 `LLM_PROVIDER=local`, private LLM 및 production service에 필요한
   환경변수가 모두 채워졌는지 확인한다.
3. `ENV=prod`, `SERVICE_MODE=production`, `KNOWLEDGE_DIR`을 설정한다. 기본 반입
   위치를 쓸 경우 Windows에서는
   `KNOWLEDGE_DIR=<backend 절대경로>\\knowledge\\production`으로 지정한다.
   `knowledge/mock`과 `knowledge/` 상위 폴더는 운영 경로로 지정하지 않는다.
   합성 mock DB 관련 변수는 설정하지 않는다.
4. 테스트를 실행할 폐쇄망 이식 환경에는 `requirements-dev.txt`를 설치하고,
   mock service·외부 provider E2E를 제외한 공통 계약 테스트를 실행한다.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q -m "not bundled_knowledge and not mock_service and not e2e"
```

5. 운영 knowledge 구조와 참조 무결성을 별도로 확인한다. 테스트가 특정
   mock 전용 이름이나 기대값을 전제하면 운영 지식용 계약 테스트로 교체한다.

```powershell
python -m pytest -q `
  tests/test_knowledge.py `
  tests/test_knowledge_integrity.py `
  tests/test_prompt_consistency.py
```

6. mock/production 서비스가 같은 공개 함수를 제공하는지 확인하고, production service에는
   실제 인프라를 호출하지 않는 단위 테스트 또는 client mock 테스트를 추가한다.
   `tests/test_production_services.py`에 이미 설정 가드레일·mock/production 공개
   시그니처 일치·`/anthropic` 미구현 상태·`missing_params` 테스트가 있다. 이식
   후에는 미구현을 단정하는 테스트를 실제 성공 경로(SQL/RAG/simulation, Result
   Store 저장 포함) 테스트로 교체하고, 프록시 501 테스트도 구현 결과에 맞게 교체한다.
7. 백엔드를 기동한다.

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --port 8100
```

8. 다른 PowerShell 창에서 `curl.exe http://localhost:8100/health`를 호출해
   `{"status":"ok"}`를 확인한다.
9. 실제 채팅으로 다음 3가지 질의를 각각
   테스트해서 production 서비스가 정상 호출되는지 확인:
   - SQL 조회가 필요한 질문 (예: 생산 실적 조회)
   - RAG 검색이 필요한 질문 (예: 공정 매뉴얼 질의)
   - Simulation이 필요한 질문 (등록된 실제 simulation type 사용)
10. Milvus 컬렉션 스키마를 `rag_service.py`(이식본)가 기대하는 필드와 대조한다
    — 특히 `chunk_index`, `doc_id`, `titles`(또는 실제 필드명), `article_path`가
    실제 컬렉션 schema에 있는지, dense/BM25 하이브리드 검색과 rerank에 필요한
    필드가 빠지지 않았는지 확인한다. 다르면 `milvus_client.py`/`rag_service.py`의
    필드 매핑을 실제 스키마에 맞춘다.
11. 등록한 모든 simulation type에 대해 실제 Simulation API 응답 JSON과
    `services/production/simulation_service.py`가 반환하는 payload(특히
    `status`, `kind`, `simulation_type`, `dataset`/`scenario`, `kpis`, Result
    Store 저장 필드)를 하나씩 대조한다. 응답 필드명이 다르면 이식 코드에서
    매핑하고, `KNOWLEDGE_DIR/simulations/*.yaml`의 `output_schema`를 실제 응답에
    맞게 갱신한다.
12. 폐쇄망 프록시 구현을 반입한 뒤 `LLM_PROVIDER=local`을 쓴다면 `/anthropic`
    경로를 별도로 검증한다: 서버를 이 설정으로 재기동한 뒤 실제 채팅 1건을 보내
    SSE 스트리밍이
    끊기지 않고 끝까지 도착하는지 확인하고, 사내 게이트웨이 접근 로그에서
    User-Agent가 차단 대상이 아닌 값으로 찍히는지 확인한다.
13. SQL 검증에서는 Agent가 운영 지식을 먼저 조회해 SQL을 생성했는지,
   `sql_service`가 SQL 생성 없이 읽기 전용 실행과 Result Store 저장만 했는지
   확인한다.
14. 문제 발생 시 mock으로 우회하지 않는다. SQL·RAG·simulation 중 실패한 production
   adapter를 로그와 client mock 테스트로 격리하고 수정한 뒤 같은 관통 검증을
   다시 실행한다.

## 2-7. 커밋 시 주의사항

- `.env` 파일은 절대 커밋하지 않는다 (`.gitignore` 확인).
- `backend/pntfp/.env`의 내용을 터미널 출력, diff, 테스트 로그와 커밋 메시지에
  노출하지 않는다.
- 반입 원본인 `backend/pntfp/`는 커밋하지 않는다. 이식 완료 후 사내 반입·보관
  정책에 따라 별도 보관하거나 안전하게 제거한다.
- `__pycache__`, `.pyc` 파일이 스테이징되지 않도록 확인한다.
- 커밋 전 `git status`로 의도치 않은 파일(사내 자료, 인증정보 등)이
  포함되지 않았는지 반드시 확인한다.
