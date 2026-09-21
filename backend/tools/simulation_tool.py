"""Simulation tool for production planning simulations."""

from services import simulation_service


async def list_simulation() -> dict:
    """List available simulation types and their required parameters.

    Use this tool first when the user's request could map to more than
    one simulation type, to discover the correct `simulation_type` and
    the parameters it requires.
    """

    return await simulation_service.list_simulation()


async def run_simulation(
    simulation_type: str, params: dict, *, access_scope: str | None = None
) -> dict:
    """Run a simulation identified by `simulation_type` with `params`.

    Example:
        simulation_type="<simulation_type>", params={"<param>": "<value>"}

    Args:
        access_scope: 요청 브라우저 세션의 불투명 scope. 모델에게 노출하지
            않고 `agent/sdk_tools.py`의 tool wrapper가 내부에서 채운다.
    """

    return await simulation_service.run_simulation(
        simulation_type=simulation_type,
        params=params,
        access_scope=access_scope,
    )
