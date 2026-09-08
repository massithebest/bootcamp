"""Simulation tool for multiple line comparison."""

from services import simulation_service


async def simulate_line_comparison(
    lines: list[str],
    period_start: str,
    period_end: str,
    metric: str = "efficiency",
) -> dict:
    """Compare multiple production lines over a date range.

    Example:
        "10월 동안 A, B, C라인 중 효율이 가장 좋은 라인은?"
    """

    return await simulation_service.run_line_comparison(
        lines=lines,
        period_start=period_start,
        period_end=period_end,
        metric=metric,
    )
