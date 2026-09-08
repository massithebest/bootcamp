"""Simulation tool for material constraints."""

from pydantic import BaseModel

from services import simulation_service


class MaterialConstraint(BaseModel):
    """Material availability constraint."""

    material_id: str
    available_qty: int


async def simulate_material_constraint(
    line: str,
    period: str,
    materials: list[MaterialConstraint],
) -> dict:
    """Simulate maximum production quantity with material constraints.

    Example:
        "자재 X 500개, Y 300개가 있을 때 A라인 최대 생산량은?"
    """

    material_payload = [
        material.model_dump()
        for material in materials
    ]

    return await simulation_service.run_material_constraint(
        line=line,
        period=period,
        materials=material_payload,
    )
