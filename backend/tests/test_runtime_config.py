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


@pytest.mark.parametrize("knowledge_dir", ["", str(BACKEND_DIR / "knowledge")])
def test_production_rejects_missing_or_bundled_knowledge(
    knowledge_dir: str,
) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "real",
            "KNOWLEDGE_DIR": knowledge_dir,
        }
    )

    assert result.returncode != 0
    assert "KNOWLEDGE_DIR" in result.stderr or "SMT2020" in result.stderr


def test_production_rejects_nonexistent_knowledge_directory(tmp_path: Path) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "real",
            "KNOWLEDGE_DIR": str(tmp_path / "missing"),
        }
    )

    assert result.returncode != 0
    assert "existing directory" in result.stderr


def test_production_selects_real_services(tmp_path: Path) -> None:
    result = run_import(
        {
            "ENV": "prod",
            "SERVICE_MODE": "real",
            "KNOWLEDGE_DIR": str(tmp_path),
        },
        "import services; print(services.sql_service.__name__)",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "services.real.sql_service"


def test_result_ui_mode_defaults_to_legacy() -> None:
    result = run_import(
        {"ENV": "dev", "RESULT_UI_MODE": "", "KNOWLEDGE_DIR": ""},
        "import core.config as config; print(config.RESULT_UI_MODE)",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "legacy"


def test_result_ui_mode_accepts_present() -> None:
    result = run_import(
        {"ENV": "dev", "RESULT_UI_MODE": "PRESENT", "KNOWLEDGE_DIR": ""},
        "import core.config as config; print(config.RESULT_UI_MODE)",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "present"


def test_invalid_result_ui_mode_is_rejected() -> None:
    result = run_import({"ENV": "dev", "RESULT_UI_MODE": "typo", "KNOWLEDGE_DIR": ""})

    assert result.returncode != 0
    assert "RESULT_UI_MODE" in result.stderr
