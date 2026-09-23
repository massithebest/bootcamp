"""Real production planning simulation service."""

from services.simulation.registry import (
    list_simulation_types,
    validate_simulation_request,
)
from services.service_logging import logged_service_operation


class ProductionSimulationService:
    """실적조회 / MP 조회 / SWAP 결과조회 등을 처리하는 실제 시뮬레이션 서비스."""

    async def list_simulation(self) -> dict:
        """List available simulation types."""

        return {"status": "ok", "simulations": list_simulation_types()}

    async def run_simulation(
        self, simulation_type: str, params: dict, *, access_scope: str | None = None
    ) -> dict:
        """Run a simulation identified by `simulation_type` with `params`."""

        validation_error = validate_simulation_request(simulation_type, params)
        if validation_error is not None:
            return validation_error

        # TODO:
        # services/production/simulation_api_client.py::SimulationApiClient.run으로
        # 실제 Simulation API 호출 (simulation_type 별 분기).
        # 결과를 Result Store에 저장할 때 mock과 동일하게 access_scope를 채운다.
        # docs/CLOSED_NETWORK_SETUP.md §2-4 참고.

        raise NotImplementedError(
            "Simulation MCP integration is not implemented."
        )


_service = ProductionSimulationService()


@logged_service_operation
async def list_simulation() -> dict:
    return await _service.list_simulation()


@logged_service_operation
async def run_simulation(
    simulation_type: str, params: dict, *, access_scope: str | None = None
) -> dict:
    return await _service.run_simulation(
        simulation_type=simulation_type, params=params, access_scope=access_scope
    )
