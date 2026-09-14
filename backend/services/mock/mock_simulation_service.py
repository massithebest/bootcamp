"""Mock production planning simulation service."""

from services.simulation_registry import (
    list_simulation_types,
    validate_simulation_request,
)


def _mock_result(simulation_type: str, params: dict) -> dict:
    if simulation_type == "실적_조회":
        return {
            "status": "ok",
            "simulation_type": simulation_type,
            "workMonthFrom": params["workMonthFrom"],
            "workMonthTo": params["workMonthTo"],
            "results": [
                {"line": "A", "workMonth": params["workMonthFrom"], "qty": 950},
            ],
        }

    if simulation_type == "MP_최신조회":
        return {
            "status": "ok",
            "simulation_type": simulation_type,
            "mpVersion": "MP-2026-09-LATEST",
            "updatedAt": "2026-09-01T00:00:00",
        }

    if simulation_type == "MP_확정조회":
        fixed_plan_month = params.get("fixedPlanMonth", "202609")
        return {
            "status": "ok",
            "simulation_type": simulation_type,
            "fixedPlanMonth": fixed_plan_month,
            "mpVersion": f"MP-{fixed_plan_month}-FIXED",
        }

    if simulation_type == "SWAP_결과조회":
        return {
            "status": "ok",
            "simulation_type": simulation_type,
            "productId": params["productId"],
            "planYm": params.get("planYm", "202609"),
            "requiredQty": 500,
            "actualQty": 480,
        }

    return {
        "status": "error",
        "message": f"알 수 없는 simulation_type 입니다: {simulation_type}",
    }


class MockSimulationService:
    """RealSimulationService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def list_simulation(self) -> dict:
        """Return mock simulation type list."""

        return {"status": "ok", "simulations": list_simulation_types()}

    async def run_simulation(self, simulation_type: str, params: dict) -> dict:
        """Return mock simulation result for the given type."""

        error = validate_simulation_request(simulation_type, params)
        if error is not None:
            return {"status": "error", "message": error}

        return _mock_result(simulation_type, params)


_service = MockSimulationService()


async def list_simulation() -> dict:
    return await _service.list_simulation()


async def run_simulation(simulation_type: str, params: dict) -> dict:
    return await _service.run_simulation(simulation_type=simulation_type, params=params)
