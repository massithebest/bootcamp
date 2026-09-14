"""Mock production planning simulation service.

`실적_조회`·`MP_확정조회` 는 합성 시드 SQLite 를 읽는다 (설계 §6-1) —
SQL 결과와 시뮬레이션 결과가 모순되면 에이전트가 잘못된 가설을 채택하므로,
두 경로가 같은 데이터를 봐야 한다.
"""

from __future__ import annotations

from services.mock._sqlite import MISSING_DB_MESSAGE, SampleDbMissingError, connect
from services.simulation_registry import (
    list_simulation_types,
    validate_simulation_request,
)


DEFAULT_PLAN_MONTH = "202609"


def _performance_lookup(params: dict) -> dict:
    """월 단위 라인별 입고 실적 합계. 취소(status_cd = 'X')는 제외한다."""

    month_from = params["workMonthFrom"]
    month_to = params["workMonthTo"]

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT line_cd AS line,
                   substr(work_date, 1, 4) || substr(work_date, 6, 2) AS workMonth,
                   SUM(inbound_qty) AS qty
              FROM FGS_INBOUND_RESULT
             WHERE status_cd <> 'X'
               AND substr(work_date, 1, 4) || substr(work_date, 6, 2) BETWEEN ? AND ?
             GROUP BY 1, 2
             ORDER BY 2, 1
            """,
            (month_from, month_to),
        ).fetchall()

    return {
        "workMonthFrom": month_from,
        "workMonthTo": month_to,
        "results": [
            {"line": row["line"], "workMonth": row["workMonth"], "qty": row["qty"]}
            for row in rows
        ],
    }


def _fixed_mp_lookup(params: dict) -> dict:
    plan_month = params.get("fixedPlanMonth") or DEFAULT_PLAN_MONTH

    with connect() as conn:
        row = conn.execute(
            "SELECT version, fixed_at, changed FROM MP_VERSION WHERE plan_month = ?",
            (plan_month,),
        ).fetchone()

    if row is None:
        return {
            "status": "error",
            "message": f"확정 MP 가 없습니다: {plan_month}",
        }

    return {
        "fixedPlanMonth": plan_month,
        "mpVersion": row["version"],
        "fixedAt": row["fixed_at"],
        "changed": row["changed"],
    }


def _mock_result(simulation_type: str, params: dict) -> dict:
    if simulation_type == "실적_조회":
        return {"status": "ok", "simulation_type": simulation_type, **_performance_lookup(params)}

    if simulation_type == "MP_확정조회":
        result = _fixed_mp_lookup(params)
        if result.get("status") == "error":
            return result
        return {"status": "ok", "simulation_type": simulation_type, **result}

    if simulation_type == "MP_최신조회":
        return {
            "status": "ok",
            "simulation_type": simulation_type,
            "mpVersion": "MP-2026-09-LATEST",
            "updatedAt": "2026-09-01T00:00:00",
        }

    if simulation_type == "SWAP_결과조회":
        return {
            "status": "ok",
            "simulation_type": simulation_type,
            "productId": params["productId"],
            "planYm": params.get("planYm", DEFAULT_PLAN_MONTH),
            "requiredQty": 500,
            "actualQty": 480,
        }

    return {
        "status": "error",
        "message": f"알 수 없는 simulation_type 입니다: {simulation_type}",
    }


class MockSimulationService:
    """RealSimulationService 와 동일한 인터페이스를 갖는 mock 구현."""

    async def list_simulation(self) -> dict:
        """Return mock simulation type list."""

        return {"status": "ok", "simulations": list_simulation_types()}

    async def run_simulation(self, simulation_type: str, params: dict) -> dict:
        """Return mock simulation result for the given type."""

        error = validate_simulation_request(simulation_type, params)
        if error is not None:
            return {"status": "error", "message": error}

        try:
            return _mock_result(simulation_type, params)
        except SampleDbMissingError:
            return {"status": "error", "message": MISSING_DB_MESSAGE}


_service = MockSimulationService()


async def list_simulation() -> dict:
    return await _service.list_simulation()


async def run_simulation(simulation_type: str, params: dict) -> dict:
    return await _service.run_simulation(simulation_type=simulation_type, params=params)
