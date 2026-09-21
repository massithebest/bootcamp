"""Shared optional fixtures for local-only development assets."""

from pathlib import Path
from types import ModuleType

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Classify every test that transitively requests the optional dataset."""

    for item in items:
        if "smt2020_assets" in item.fixturenames:
            item.add_marker(pytest.mark.smt2020)
            item.add_marker(pytest.mark.mock_service)
        if "bundled_knowledge" in item.fixturenames:
            item.add_marker(pytest.mark.smt2020_bundle)


@pytest.fixture(scope="session")
def smt2020_assets() -> ModuleType:
    """Load the ignored SMT2020 builder only when all local assets exist."""

    backend_dir = Path(__file__).resolve().parent.parent
    builder = backend_dir / "scripts" / "build_smt2020_db.py"
    source_root = backend_dir / "datasets"
    source_dirs = [
        source_root / "SMT2020_HVLM",
        source_root / "SMT2020_LVHM",
    ]
    if not builder.is_file() or not all(path.is_dir() for path in source_dirs):
        pytest.skip(
            "SMT2020 local development assets are unavailable; "
            "dataset-backed mock regression test skipped"
        )

    from scripts import build_smt2020_db

    return build_smt2020_db


@pytest.fixture()
def bundled_knowledge(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the knowledge store at the bundled SMT2020 YAML, ignoring KNOWLEDGE_DIR."""

    from core.config import DEFAULT_KNOWLEDGE_DIR
    from services import knowledge_service

    monkeypatch.setattr(knowledge_service, "KNOWLEDGE_DIR", DEFAULT_KNOWLEDGE_DIR)
    knowledge_service.reset_store()
    yield DEFAULT_KNOWLEDGE_DIR
    knowledge_service.reset_store()
