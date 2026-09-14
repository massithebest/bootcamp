"""Simulation type / parameter schema shared by mock and real services."""

from typing import Any


SIMULATION_TYPES: dict[str, dict[str, Any]] = {
    "실적_조회": {
        "name": "실적조회",
        "aliases": ["생산실적 조회", "실적 시뮬레이션"],
        "required_params": ["workMonthFrom", "workMonthTo"],
    },
    "MP_최신조회": {
        "name": "최신 MP 조회",
        "aliases": ["최신 MP", "MP 버전", "확정 MP 버전"],
        "required_params": [],
    },
    "MP_확정조회": {
        "name": "확정 MP 조회",
        "aliases": ["확정 MP", "확정된 버전", "확정 MP 버전"],
        "required_params": [],
    },
    "SWAP_결과조회": {
        "name": "SWAP 결과 조회",
        "aliases": ["SWAP 실행 결과", "단품 필요량 계획 및 실적", "계획 및 실적조회"],
        "required_params": ["productId"],
    },
}

PARAM_SCHEMA: dict[str, dict[str, Any]] = {
    "workMonthFrom": {
        "required": True,
        "description": "조회 시작 작업 월 (yyyyMM, 포함)",
        "example": "202608",
    },
    "workMonthTo": {
        "required": True,
        "description": "조회 끝 작업 월 (yyyyMM, 포함)",
        "example": "202608",
    },
    "fixedPlanMonth": {
        "required": False,
        "description": "확정 MP 조회 연월 (yyyyMM), 누락시 당월 사용",
    },
    "productId": {
        "required": True,
        "description": "필요량 품목 ID",
        "example": "0000000000-00001",
    },
    "workDt": {
        "required": False,
        "description": "작업일 (yyyyMMdd), 누락시 기준일 자동 사용",
    },
    "planYm": {
        "required": False,
        "description": "계획월 (yyyyMM), 누락시 당월 사용",
    },
}


def validate_simulation_request(simulation_type: str, params: dict[str, Any]) -> str | None:
    """Return an error message if the request is invalid, otherwise None."""

    simulation = SIMULATION_TYPES.get(simulation_type)
    if simulation is None:
        return f"알 수 없는 simulation_type 입니다: {simulation_type}"

    missing = [
        name
        for name in simulation["required_params"]
        if name not in params or params[name] in (None, "")
    ]
    if missing:
        return f"필수 파라미터가 누락되었습니다: {', '.join(missing)}"

    return None


def list_simulation_types() -> list[dict[str, Any]]:
    return [
        {"type": simulation_type, **meta}
        for simulation_type, meta in SIMULATION_TYPES.items()
    ]
