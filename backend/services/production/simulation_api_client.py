"""사내 Simulation API 클라이언트 스텁.

폐쇄망 이식 대상이다. 반입되는 `simulation_api_client.py`(문서 철자 오류
`sumulation_api_client.py`의 정정본, `docs/CLOSED_NETWORK_SETUP.md` §2-1)의
실제 Simulation API 호출 로직을 여기에 병합한다.
"""

from core.config import SIMULATION_API_URL, require_production_env


class SimulationApiClient:
    """사내 Simulation API를 호출하는 클라이언트."""

    async def run(self, simulation_type: str, params: dict) -> dict:
        """등록된 `simulation_type`을 실제 Simulation API로 실행한다.

        이식 시 주의: `simulation_type`/필수 파라미터 검증은 호출자인
        `services/production/simulation_service.py`가 `validate_simulation_request()`로
        먼저 처리하므로 여기서 중복 검증하지 않는다.
        """

        require_production_env("SIMULATION_API_URL", SIMULATION_API_URL)

        # TODO: 폐쇄망 pntfp의 simulation_api_client.py 호출 로직 이식
        raise NotImplementedError(
            "SimulationApiClient.run은 폐쇄망 이식 대상입니다. "
            "docs/CLOSED_NETWORK_SETUP.md §2-4 참고."
        )
