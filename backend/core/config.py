"""Application configuration.

`.env` 파일이 있으면 로드한다. (python-dotenv 미설치 시 무시)
실제 환경변수가 항상 우선한다.
"""

import os
import shutil
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ModuleNotFoundError:  # pragma: no cover
    pass


# ---- 애플리케이션 ----
ENV = os.getenv("ENV", "dev")

SERVICE_MODE = os.getenv("SERVICE_MODE", "mock")

#: backend/ 디렉터리. 아래 경로 상수의 기준점.
BACKEND_DIR = Path(__file__).resolve().parent.parent

#: 도메인 지식 YAML(카탈로그·KPI·시뮬레이션·용어집·시나리오) 루트.
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR") or BACKEND_DIR / "knowledge")

#: 합성 시드 SQLite 경로. `python -m scripts.seed_sample_db` 산출물이며 git 추적 대상이 아니다.
SAMPLE_DB_PATH = Path(os.getenv("SAMPLE_DB_PATH") or BACKEND_DIR / "data" / "sample.sqlite")

#: CORS 허용 Origin 목록. 개발 환경의 Frontend dev 서버만 허용한다.
#: 콤마로 구분해 환경변수(CORS_ALLOW_ORIGINS)로 재정의할 수 있다.
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]


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
