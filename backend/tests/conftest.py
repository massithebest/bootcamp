"""Shared fixtures for the git-tracked synthetic mock dataset."""

from pathlib import Path
from types import ModuleType

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Classify every test that transitively requests the mock dataset."""

    for item in items:
        if "mock_database" in item.fixturenames:
            item.add_marker(pytest.mark.mock_service)
        if "bundled_knowledge" in item.fixturenames:
            item.add_marker(pytest.mark.bundled_knowledge)


@pytest.fixture(scope="session")
def mock_database() -> ModuleType:
    """The synthetic mock database generator (always available; git-tracked)."""

    from scripts import generate_mock_database

    return generate_mock_database


@pytest.fixture()
def bundled_knowledge(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the knowledge store at the bundled mock YAML, ignoring KNOWLEDGE_DIR."""

    from core.config import DEFAULT_KNOWLEDGE_DIR
    from services.knowledge import catalog as knowledge_service

    monkeypatch.setattr(knowledge_service, "KNOWLEDGE_DIR", DEFAULT_KNOWLEDGE_DIR)
    knowledge_service.reset_store()
    yield DEFAULT_KNOWLEDGE_DIR
    knowledge_service.reset_store()
