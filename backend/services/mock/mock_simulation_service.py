"""Mock production planning simulation services."""


async def run_line_capacity(
    line: str,
    period: str,
    target_qty: int,
) -> dict:
    """Return mock line capacity result."""

    return {
        "status": "ok",
        "line": line,
        "period": period,
        "target_qty": target_qty,
        "achievable_qty": 950,
        "achievement_rate": 0.95,
        "bottleneck": "설비 가동률",
    }


async def run_material_constraint(
    line: str,
    period: str,
    materials: list[dict],
) -> dict:
    """Return mock material constraint result."""

    return {
        "status": "ok",
        "line": line,
        "period": period,
        "max_producible_qty": 780,
        "limiting_material": (
            materials[0]["material_id"]
            if materials
            else None
        ),
        "material_usage": [
            {
                "material_id": material["material_id"],
                "required": 200,
                "available": material["available_qty"],
            }
            for material in materials
        ],
    }


async def run_line_comparison(
    lines: list[str],
    period_start: str,
    period_end: str,
    metric: str,
) -> dict:
    """Return mock line comparison result."""

    return {
        "status": "ok",
        "period_start": period_start,
        "period_end": period_end,
        "metric": metric,
        "ranking": [
            {
                "line": line,
                "score": 0.9 - index * 0.05,
                "rank": index + 1,
            }
            for index, line in enumerate(lines)
        ],
    }
