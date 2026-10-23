"""SQL 방언 안내: Agent 가 DB 방언에 맞는 함수·날짜 문법을 쓰도록 알린다."""

import asyncio

import pytest

from agent.sdk_tools import planning_tools, sql_dialect_note
from services.mock import mock_sql_service
from services.production import sql_service as production_sql_service
from services.results import store as result_store
from services.results.store import LocalParquetResultStore


def test_mock_and_production_services_expose_the_same_dialect_attribute() -> None:
    assert mock_sql_service.SQL_DIALECT == "SQLite"
    assert isinstance(production_sql_service.SQL_DIALECT, str)


def test_execute_sql_description_names_the_dialect_and_sqlite_equivalents(monkeypatch) -> None:
    monkeypatch.setattr("services.sql_service.SQL_DIALECT", "SQLite", raising=False)
    description = next(t for t in planning_tools("scope") if t.name == "execute_sql").description

    assert "SQL 방언은 SQLite" in description
    assert "NVL→COALESCE" in description and "strftime('%Y%m', 'now', 'localtime')" in description
    # YYYYMMDD 문자열에 strftime 을 쓰면 NULL 이 되어 "월이 비어 있다"는 오판으로 이어졌다.
    assert "substr(컬럼, 1, 6)" in description and "저장 형식" in description


def test_unknown_dialect_adds_no_note(monkeypatch) -> None:
    monkeypatch.setattr("services.sql_service.SQL_DIALECT", "", raising=False)
    assert sql_dialect_note() == ""

    monkeypatch.setattr("services.sql_service.SQL_DIALECT", "Oracle", raising=False)
    note = sql_dialect_note()
    assert "SQL 방언은 Oracle" in note and "strftime" not in note


@pytest.mark.mock_service
def test_mock_sql_error_mentions_the_dialect(tmp_path, monkeypatch, mock_database) -> None:
    monkeypatch.setattr("core.config.MOCK_DB_PATH", mock_database.main(tmp_path / "mock_planning.db"))
    monkeypatch.setattr(result_store, "_store", LocalParquetResultStore(tmp_path / "results"))

    result = asyncio.run(mock_sql_service.execute_sql(
        "SELECT TO_CHAR(WORK_DT, 'YYYYMM') FROM FP_TARGET", "방언 오류 확인"))

    assert result["status"] == "error"
    assert "no such function" in result["message"] and "SQLite" in result["message"]
