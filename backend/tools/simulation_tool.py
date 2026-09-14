"""Simulation tool for production planning simulations."""

from services import simulation_service


async def list_simulation() -> dict:
    """List available simulation types and their required parameters.

    Use this tool first when the user's request could map to more than
    one simulation type, to discover the correct `simulation_type` and
    the parameters it requires.
    """

    return await simulation_service.list_simulation()


async def run_simulation(simulation_type: str, params: dict) -> dict:
    """Run a simulation identified by `simulation_type` with `params`.

    Example:
        simulation_type="실적_조회", params={"workMonthFrom": "202608", "workMonthTo": "202608"}
    """

    return await simulation_service.run_simulation(
        simulation_type=simulation_type,
        params=params,
    )
