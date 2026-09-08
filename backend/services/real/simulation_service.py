"""Real production planning simulation service."""


async def run_line_capacity(
    line: str,
    period: str,
    target_qty: int,
) -> dict:
    """Run line capacity simulation."""

    # TODO:
    # 실제 Simulation MCP Server 호출

    raise NotImplementedError(
        "Simulation MCP integration is not implemented."
    )


async def run_material_constraint(
    line: str,
    period: str,
    materials: list[dict],
) -> dict:
    """Run material constraint simulation."""

    # TODO:
    # 실제 Simulation MCP Server 호출

    raise NotImplementedError(
        "Simulation MCP integration is not implemented."
    )


async def run_line_comparison(
    lines: list[str],
    period_start: str,
    period_end: str,
    metric: str,
) -> dict:
    """Run line comparison simulation."""

    # TODO:
    # 실제 Simulation MCP Server 호출

    raise NotImplementedError(
        "Simulation MCP integration is not implemented."
    )
