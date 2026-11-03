"""Runtime mode isolation for development mocks and closed-network production."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_import(
    env: dict[str, str], statement: str = "import core.config"
) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    process_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", statement],
        cwd=BACKEND_DIR,
        env=process_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_development_defaults_to_mock() -> None:
    result = run_import(
        {"ENV": "dev", "SERVICE_MODE": "", "KNOWLEDGE_DIR": ""},
        "import core.config as config; print(config.SERVICE_MODE)",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "mock"


def test_invalid_service_mode_is_rejected_in_development() -> None:
    result = run_import(
        {"ENV": "dev", "SERVICE_MODE": "typo", "KNOWLEDGE_DIR": ""}
    )

    assert result.returncode != 0
    assert "SERVICE_MODE" in result.stderr


def test_production_rejects_mock_service_mode(tmp_path: Path) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "mock",
            "KNOWLEDGE_DIR": str(tmp_path),
        }
    )

    assert result.returncode != 0
    assert "SERVICE_MODE" in result.stderr


@pytest.mark.parametrize(
    "knowledge_dir",
    ["", str(BACKEND_DIR / "knowledge"), str(BACKEND_DIR / "knowledge" / "mock")],
)
def test_production_rejects_missing_or_bundled_knowledge(
    knowledge_dir: str,
) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "production",
            "KNOWLEDGE_DIR": knowledge_dir,
        }
    )

    assert result.returncode != 0
    assert "KNOWLEDGE_DIR" in result.stderr or "mock" in result.stderr


def test_production_accepts_bundled_production_knowledge_directory() -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "production",
            "KNOWLEDGE_DIR": str(BACKEND_DIR / "knowledge" / "production"),
        }
    )

    assert result.returncode == 0


def test_production_rejects_nonexistent_knowledge_directory(tmp_path: Path) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "production",
            "KNOWLEDGE_DIR": str(tmp_path / "missing"),
        }
    )

    assert result.returncode != 0
    assert "existing directory" in result.stderr


def test_production_selects_production_services(tmp_path: Path) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "production",
            "KNOWLEDGE_DIR": str(tmp_path),
        },
        "import services; print(services.sql_service.__name__)",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "services.production.sql_service"


def test_real_service_mode_is_accepted_as_compatibility_alias(tmp_path: Path) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "real",
            "KNOWLEDGE_DIR": str(tmp_path),
        },
        "import core.config as config; import services; print(config.SERVICE_MODE, services.sql_service.__name__)",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "production services.production.sql_service"


def test_agent_runtime_defaults_to_openai_and_rejects_unknown_values() -> None:
    default = run_import(
        {"ENV": "dev", "SERVICE_MODE": "", "KNOWLEDGE_DIR": "", "AGENT_RUNTIME": ""},
        "import core.config as config; print(config.AGENT_RUNTIME)",
    )
    typo = run_import({"ENV": "dev", "SERVICE_MODE": "", "KNOWLEDGE_DIR": "", "AGENT_RUNTIME": "gpt"})

    assert default.returncode == 0 and default.stdout.strip() == "openai"
    assert typo.returncode != 0 and "AGENT_RUNTIME" in typo.stderr


def test_openai_runtime_reports_missing_gateway_settings_by_name(monkeypatch) -> None:
    from core import config

    monkeypatch.setattr(config, "AGENT_RUNTIME", "openai")
    monkeypatch.setattr(config, "AZURE_OPENAI_ENDPOINT", "")
    monkeypatch.setattr(config, "AZURE_OPENAI_API_KEY", "secret-value")
    monkeypatch.setattr(config, "AZURE_OPENAI_DEPLOYMENT", "")

    assert config.missing_agent_runtime_settings() == ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]

    monkeypatch.setattr(config, "AGENT_RUNTIME", "claude")
    assert config.missing_agent_runtime_settings() == []


#: 해당 패키지가 설치되지 않은 환경을 흉내 낸 뒤 앱을 import 하고 첫 채팅 실행부를 고른다.
_WITHOUT_PACKAGE = """
import asyncio, sys
from importlib.abc import MetaPathFinder

class Block(MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] == {blocked!r}:
            raise ImportError(name + " is not installed")

sys.meta_path.insert(0, Block())
import main
from agent import agent
import agent.{runtime}
print("loaded", "agent.{other}" in sys.modules)
"""


@pytest.mark.parametrize(
    ("runtime", "blocked", "other"),
    [("openai", "claude_agent_sdk", "claude_runtime"), ("claude", "agents", "openai_runtime")],
)
def test_app_imports_without_the_unused_runtime_package(runtime, blocked, other) -> None:
    # 기본 OpenAI 실행부만 쓰는 폐쇄망 설치에 claude-agent-sdk 가 없어도 앱이 떠야 한다(반대도 같다).
    result = run_import(
        {"ENV": "dev", "SERVICE_MODE": "mock", "AGENT_RUNTIME": runtime},
        _WITHOUT_PACKAGE.format(
            blocked=blocked, runtime=f"{runtime}_runtime", other=other
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "loaded False"
