"""Simulation tool for line capacity."""

from services import simulation_service


async def simulate_line_capacity(
    line: str,
    period: str,
    target_qty: int,
) -> dict:
    """Simulate whether a production target can be achieved.

    Example:
        "9월에 A라인에서 1000개 생산 가능한가?"
    """

    return await simulation_service.run_line_capacity(
        line=line,
        period=period,
        target_qty=target_qty,
    )
