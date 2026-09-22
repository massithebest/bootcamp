"""Application configuration.

`.env` 파일이 있으면 로드한다. (python-dotenv 미설치 시 무시)
실제 환경변수가 항상 우선한다.
"""

import json
import os
import shutil
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ModuleNotFoundError:  # pragma: no cover
    pass


# ---- 애플리케이션 ----
ENV = os.getenv("ENV", "").strip().lower() or "dev"

SERVICE_MODE = os.getenv("SERVICE_MODE", "").strip().lower() or "mock"

#: backend/ 디렉터리. 아래 경로 상수의 기준점.
BACKEND_DIR = Path(__file__).resolve().parent.parent

#: 도메인 지식 YAML(카탈로그·KPI·시뮬레이션·용어집·시나리오) 루트.
DEFAULT_KNOWLEDGE_DIR = BACKEND_DIR / "knowledge"
_CONFIGURED_KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "").strip()
KNOWLEDGE_DIR = Path(_CONFIGURED_KNOWLEDGE_DIR or DEFAULT_KNOWLEDGE_DIR)

#: 개발용 mock에서만 사용하는 SMT2020 SQLite 경로.
#: 폐쇄망 운영(`ENV=prod`)은 real service만 사용하므로 이 값을 참조하지 않는다.
SMT2020_DB_PATH = Path(
    os.getenv("SMT2020_DB_PATH") or BACKEND_DIR / "datasets" / "smt2020.db"
)


def validate_runtime_configuration() -> None:
    """Fail fast when service or production knowledge isolation is unsafe."""

    if SERVICE_MODE not in {"mock", "real"}:
        raise RuntimeError("SERVICE_MODE must be either 'mock' or 'real'.")

    if ENV != "prod":
        return

    if SERVICE_MODE != "real":
        raise RuntimeError("ENV=prod requires SERVICE_MODE=real.")
    if not _CONFIGURED_KNOWLEDGE_DIR:
        raise RuntimeError("ENV=prod requires an explicit KNOWLEDGE_DIR.")
    if not KNOWLEDGE_DIR.is_dir():
        raise RuntimeError("ENV=prod requires KNOWLEDGE_DIR to be an existing directory.")
    if KNOWLEDGE_DIR.resolve() == DEFAULT_KNOWLEDGE_DIR.resolve():
        raise RuntimeError(
            "ENV=prod cannot use the bundled SMT2020 development knowledge directory."
        )


validate_runtime_configuration()

#: 조회 결과(parquet) 저장 디렉터리. git 추적 대상이 아니다.
RESULT_STORE_DIR = Path(
    os.getenv("RESULT_STORE_DIR") or BACKEND_DIR / "data" / "results"
)

#: 조회 결과 보존 시간과 결과 저장소의 최대 디스크 사용량.
RESULT_STORE_TTL_HOURS = int(os.getenv("RESULT_STORE_TTL_HOURS") or "24")
RESULT_STORE_MAX_BYTES = int(
    os.getenv("RESULT_STORE_MAX_BYTES") or str(500 * 1024 * 1024)
)

#: CORS 허용 Origin 목록. 개발 환경의 Frontend dev 서버만 허용한다.
#: 콤마로 구분해 환경변수(CORS_ALLOW_ORIGINS)로 재정의할 수 있다.
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3100,http://127.0.0.1:3100",
    ).split(",")
    if origin.strip()
]

#: 결과·시각화 접근 범위를 구분하는 불투명 브라우저 세션 쿠키 이름.
#: 인증 principal이 아니다 — "같은 브라우저가 만든 결과인지" 구분용
#: (`plan/Todo.md`의 결과·시각화 안정 계약).
SESSION_SCOPE_COOKIE_NAME = "pp_session_scope"

#: 쿠키의 Secure 속성. 로컬 개발(HTTP)에서는 꺼야 브라우저가 쿠키를 저장한다.
#: 운영 배포(HTTPS)에서는 반드시 켠다. ENV=prod일 때만 True.
SESSION_COOKIE_SECURE = ENV == "prod"


# ---- LLM Provider ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()

#: Agent 가 사용할 모델. 비어 있으면 Claude Code 기본값을 쓴다.
AGENT_MODEL = os.getenv("AGENT_MODEL") or None

#: Claude Code CLI(`claude`) 실행 파일 경로.
#: PATH 에 없어도 되도록 명시 경로 -> PATH 탐색 순으로 결정한다.
#: 둘 다 실패하면 None 이며, SDK 가 자체 탐색 후 없으면 CLINotFoundError 를 낸다.
CLAUDE_CLI_PATH = os.getenv("CLAUDE_CLI_PATH") or shutil.which("claude") or None


def agent_provider_env() -> dict[str, str]:
    """Claude Agent SDK(CLI)에 주입할 Provider 환경변수를 구성한다.

    - anthropic  : 기본 동작. 별도 주입 없음(ANTHROPIC_API_KEY 그대로 사용).
    - openrouter : base URL 을 OpenRouter 로 바꾸고 bearer 토큰으로 인증한다.
    """

    if LLM_PROVIDER == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api")
        return {
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_AUTH_TOKEN": api_key,
            # Anthropic 직결 fallback 방지를 위해 명시적으로 비운다.
            "ANTHROPIC_API_KEY": "",
        }

    return {}

# 텍스트 지식 저장소. 생산 DB와 분리하며 TTL로 삭제하지 않는다.
KNOWLEDGE_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH") or BACKEND_DIR / "data" / "knowledge.sqlite3")
# local은 SQL의 mock/real 모드와 독립. service는 향후 사내 RAG 어댑터용.
KNOWLEDGE_SEARCH_BACKEND = os.getenv("KNOWLEDGE_SEARCH_BACKEND", "local")

# ---- 구조화 지식 관리(변경 요청·승인) ----
# 인증 체계가 생기기 전까지 쓰는 스텁 principal 설정이다. 보안 경계가 아니라
# 작성자·승인자를 구분해 기록하기 위한 값이며, 실제 인증이 붙으면
# `core/principal.py::current_principal`만 교체한다.
KNOWLEDGE_PERMISSION_WRITE = "knowledge:write"
KNOWLEDGE_PERMISSION_APPROVE = "knowledge:approve"

#: false 이면 변경 요청 API의 쓰기 동작을 모두 막는다. 조회는 계속 가능하다.
KNOWLEDGE_MANAGEMENT_ENABLED = (
    os.getenv("KNOWLEDGE_MANAGEMENT_ENABLED", "true").strip().lower()
    not in {"0", "false", "no", "off"}
)

#: 작성자와 승인자가 같은 principal이어도 승인을 허용할지 여부. 기본은 차단한다.
KNOWLEDGE_ALLOW_SELF_APPROVAL = (
    os.getenv("KNOWLEDGE_ALLOW_SELF_APPROVAL", "false").strip().lower()
    in {"1", "true", "yes", "on"}
)

_DEFAULT_KNOWLEDGE_PRINCIPALS: dict[str, dict] = {
    "user": {"name": "사용자", "permissions": [KNOWLEDGE_PERMISSION_WRITE]},
    "admin": {
        "name": "관리자",
        "permissions": [KNOWLEDGE_PERMISSION_WRITE, KNOWLEDGE_PERMISSION_APPROVE],
    },
}


def _load_knowledge_principals() -> dict[str, dict]:
    """`KNOWLEDGE_PRINCIPALS` JSON({id: {name, permissions[]}})을 검증해 읽는다."""

    raw = os.getenv("KNOWLEDGE_PRINCIPALS", "").strip()
    if not raw:
        return _DEFAULT_KNOWLEDGE_PRINCIPALS
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("KNOWLEDGE_PRINCIPALS must be valid JSON.") from exc
    allowed = {KNOWLEDGE_PERMISSION_WRITE, KNOWLEDGE_PERMISSION_APPROVE}
    if not isinstance(parsed, dict) or not parsed:
        raise RuntimeError("KNOWLEDGE_PRINCIPALS must be a non-empty JSON object.")
    principals: dict[str, dict] = {}
    for principal_id, entry in parsed.items():
        permissions = entry.get("permissions") if isinstance(entry, dict) else None
        if (
            not isinstance(principal_id, str)
            or not principal_id.strip()
            or not isinstance(permissions, list)
            or not set(permissions) <= allowed
        ):
            raise RuntimeError(
                "KNOWLEDGE_PRINCIPALS entries need an id and known permissions."
            )
        name = entry.get("name") or principal_id
        principals[principal_id] = {"name": str(name), "permissions": list(permissions)}
    return principals


KNOWLEDGE_PRINCIPALS = _load_knowledge_principals()

#: `X-User-Id` 헤더가 없을 때 쓰는 principal id. 비우면 권한이 가장 적은 항목.
KNOWLEDGE_DEFAULT_PRINCIPAL = os.getenv("KNOWLEDGE_DEFAULT_PRINCIPAL", "").strip() or min(
    KNOWLEDGE_PRINCIPALS, key=lambda key: len(KNOWLEDGE_PRINCIPALS[key]["permissions"])
)
if KNOWLEDGE_DEFAULT_PRINCIPAL not in KNOWLEDGE_PRINCIPALS:
    raise RuntimeError("KNOWLEDGE_DEFAULT_PRINCIPAL must be one of KNOWLEDGE_PRINCIPALS.")
