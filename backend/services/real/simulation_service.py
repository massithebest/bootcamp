"""Real production planning simulation service."""

from services.simulation_registry import (
    list_simulation_types,
    validate_simulation_request,
)


class RealSimulationService:
    """실적조회 / MP 조회 / SWAP 결과조회 등을 처리하는 실제 시뮬레이션 서비스."""

    async def list_simulation(self) -> dict:
        """List available simulation types."""

        return {"status": "ok", "simulations": list_simulation_types()}

    async def run_simulation(self, simulation_type: str, params: dict) -> dict:
        """Run a simulation identified by `simulation_type` with `params`."""

        error = validate_simulation_request(simulation_type, params)
        if error is not None:
            return {"status": "error", "message": error}

        # TODO:
        # 실제 Simulation MCP Server 호출 (simulation_type 별 분기)

        raise NotImplementedError(
            "Simulation MCP integration is not implemented."
        )


_service = RealSimulationService()


async def list_simulation() -> dict:
    return await _service.list_simulation()


async def run_simulation(simulation_type: str, params: dict) -> dict:
    return await _service.run_simulation(simulation_type=simulation_type, params=params)
