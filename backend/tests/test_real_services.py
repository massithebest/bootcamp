"""client mock 기반 production 경계 회귀 테스트.

폐쇄망 인프라(사내 SQL API·Milvus·Simulation API·LLM 게이트웨이) 없이도
검증 가능한 것만 담는다: production 어댑터의 설정 가드레일, `/anthropic`
프록시 미구현 상태, `missing_params` 구조화 상태.

TODO: 폐쇄망에서 `services/production/{sql,rag,simulation}_service.py`에 실제
HTTP 로직이 이식된 뒤에는, 이 파일에 성공 경로(Result Store 저장 포함) 테스트를
추가한다(`docs/CLOSED_NETWORK_SETUP.md` §2-6-6).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from main import app
from services.mock import mock_simulation_service
from services.production.common_sql_client import CommonSqlClient
from services.production.milvus_client import get_embedding_function, get_milvus_client
from services.production.rag_service import ProductionRAGService
from services.production.simulation_api_client import SimulationApiClient
from services.production.simulation_service import ProductionSimulationService
from services.production.sql_service import ProductionSQLService
from services.simulation.registry import validate_simulation_request


# ---- production 어댑터 가드레일: 필수 환경변수가 비어 있으면 명확한 오류 ----


def test_common_sql_client_requires_endpoint_config() -> None:
    with pytest.raises(RuntimeError, match="COMMON_SQL_API_URL"):
        asyncio.run(CommonSqlClient().execute("SELECT 1"))


def test_simulation_api_client_requires_endpoint_config() -> None:
    with pytest.raises(RuntimeError, match="SIMULATION_API_URL"):
        asyncio.run(SimulationApiClient().run("입력_정합성_검증", {"dataset": "SEG_A"}))


def test_milvus_client_requires_embedding_config() -> None:
    with pytest.raises(RuntimeError, match="IFLOW_EMBEDDING_ENDPOINT"):
        get_embedding_function()


def test_milvus_client_requires_connection_config() -> None:
    with pytest.raises(RuntimeError, match="MILVUS_HOST"):
        get_milvus_client()


def test_production_services_are_not_implemented_yet() -> None:
    """이식 전에는 mock으로 우회하지 않고 명확히 NotImplementedError를 낸다."""

    with pytest.raises(NotImplementedError):
        asyncio.run(ProductionSQLService().execute_sql("SELECT 1", purpose="p"))
    with pytest.raises(NotImplementedError):
        asyncio.run(ProductionRAGService().search("query"))
    with pytest.raises(NotImplementedError):
        asyncio.run(
            ProductionSimulationService().run_simulation(
                "입력_정합성_검증", {"dataset": "SEG_A"}
            )
        )


# ---- missing_params 구조화 상태 ----


def test_registry_reports_missing_params_structurally() -> None:
    result = validate_simulation_request("입력_정합성_검증", {})

    assert result is not None
    assert result["status"] == "missing_params"
    assert result["missing"][0]["name"] == "dataset"
    assert isinstance(result["missing"][0]["description"], str)


def test_registry_reports_error_for_unknown_type() -> None:
    result = validate_simulation_request("존재하지-않는-종류", {"dataset": "SEG_A"})

    assert result == {
        "status": "error",
        "message": "알 수 없는 simulation_type 입니다: 존재하지-않는-종류",
    }


def test_mock_run_simulation_returns_missing_params_without_touching_db() -> None:
    """DB가 없어도(=관계 검증 전에) missing_params로 끝나야 한다."""

    result = asyncio.run(
        mock_simulation_service.run_simulation("입력_정합성_검증", {})
    )

    assert result["status"] == "missing_params"
    assert result["missing"][0]["name"] == "dataset"


# ---- /anthropic 프록시: 폐쇄망 구현 반입 전 미구현 상태 ----


def test_anthropic_proxy_is_unimplemented_until_closed_network_code_is_imported() -> None:
    client = TestClient(app)

    response = client.post(
        "/anthropic/v1/messages",
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 501
    assert "폐쇄망 구현 반입 후" in response.json()["detail"]
