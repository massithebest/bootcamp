"""Simulation type / parameter schema shared by mock and real services.

정의의 source of truth 는 `knowledge/simulations/*.yaml` 이다 (설계 §3).
이 모듈은 그것을 로드해 서비스·tool 이 쓰는 형태로 돌려주는 얇은 계층이다.
새 시뮬레이션 종류는 YAML 파일을 추가하면 된다.
"""

from typing import Any

from services.knowledge_service import get_store
from services.service_logging import logged_service_operation


@logged_service_operation
def validate_simulation_request(simulation_type: str, params: dict[str, Any]) -> str | None:
    """Return an error message if the request is invalid, otherwise None."""

    store = get_store()
    if not store.is_simulation_active(simulation_type):
        return f"알 수 없는 simulation_type 입니다: {simulation_type}"
    simulation = store.simulations[simulation_type]

    missing = [
        name
        for name, param in simulation.params.items()
        if param.required and (name not in params or params[name] in (None, ""))
    ]
    if missing:
        return f"필수 파라미터가 누락되었습니다: {', '.join(missing)}"

    return None


@logged_service_operation
def list_simulation_types() -> list[dict[str, Any]]:
    """종류·파라미터 상세·사용 시점·출력 스키마·선후 관계를 함께 돌려준다."""

    return get_store().list_simulations()
