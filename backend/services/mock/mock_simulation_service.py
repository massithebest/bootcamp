"""Dataset-backed mock simulation service for synthetic mock input validation.

This deliberately does not claim to run a discrete-event simulation. It checks
that a selected segment has the input relationships a simulator would need.
"""

from __future__ import annotations

import pandas as pd

from services.mock._sqlite import MISSING_DB_MESSAGE, MockDbMissingError, connect
from services.mock.mock_pkt_swap import PKT_SWAP_SIMULATION_TYPE, generate_pkt_swap_response
from services.results.query import PREVIEW_SAMPLE_ROWS, tool_preview
from services.results.store import get_result_store
from services.service_logging import logged_service_operation
from services.simulation.registry import list_simulation_types, validate_simulation_request


SIMULATION_TYPE = "입력_정합성_검증"

_PKT_SWAP_ITEM_COLUMNS = [
    "planProductId", "planYm", "planVersion", "osCode", "fabId", "site", "grade",
    "customer", "planQty", "poutQty", "targetQty",
    "swap_swapId", "swap_direction", "swap_prodGrpNm", "swap_gbnCd",
    "swap_frParaVal", "swap_toParaVal", "swap_swapQty",
    "swap_counterPlanProdId", "swap_counterSite", "swap_counterGrade", "swap_counterCsCode",
]


def _flatten_pkt_swap_item(item: dict) -> list:
    reason = item.get("swapReason") or {}
    return [
        item["planProductId"], item["planYm"], item["planVersion"], item["osCode"],
        item["fabId"], item["site"], item["grade"], item["customer"],
        item["planQty"], item["poutQty"], item["targetQty"],
        reason.get("swapId"), reason.get("direction"), reason.get("prodGrpNm"),
        reason.get("gbnCd"), reason.get("frParaVal"), reason.get("toParaVal"),
        reason.get("swapQty"), reason.get("counterPlanProdId"), reason.get("counterSite"),
        reason.get("counterGrade"), reason.get("counterCsCode"),
    ]


def _pkt_swap_tool_result(response: dict, *, access_scope: str | None) -> dict:
    metadata = response["metadata"]
    items = response["items"]
    rows = [_flatten_pkt_swap_item(item) for item in items]
    meta = get_result_store().save(
        _PKT_SWAP_ITEM_COLUMNS,
        rows,
        source=f"run_simulation:{PKT_SWAP_SIMULATION_TYPE}",
        conversation_id=None,
        access_scope=access_scope,
    )
    summary = (
        f"{metadata['itemCount']}개 행 중 swap {metadata['swapCount']}건. "
        "이 결과는 합성 mock 데이터를 재현한 것으로 실제 스냅샷 수치가 아닙니다."
    )
    return tool_preview(
        meta,
        pd.DataFrame(rows, columns=_PKT_SWAP_ITEM_COLUMNS),
        kind="simulation",
        simulation_type=PKT_SWAP_SIMULATION_TYPE,
        scenario="PKT 목표수량 swap 산출",
        summary=summary,
        kpis=[
            {"label": "행 수", "value": metadata["itemCount"], "unit": "건"},
            {"label": "Swap 발생", "value": metadata["swapCount"], "unit": "건"},
            {"label": "목표수량 합계", "value": metadata["totalTarget"], "unit": ""},
            {"label": "계획수량 합계", "value": metadata["totalPlanQty"], "unit": ""},
        ],
    )


ALLOWED_DATASETS = {"SEG_A", "SEG_B"}
INPUT_TABLES = (
    "part", "route_step", "tool", "orders", "wip", "setup", "setup_group",
    "down_calendar", "pm_calendar", "calendar_attach", "transport",
)

RELATION_CHECKS = (
    (
        "part_to_route_step",
        "part",
        """
        SELECT COUNT(*) FROM part source
         WHERE source.dataset = ?
           AND NOT EXISTS (
               SELECT 1 FROM route_step target
                WHERE target.dataset = source.dataset AND target.route = source.route
           )
        """,
    ),
    (
        "route_step_to_tool",
        "route_step",
        """
        SELECT COUNT(*) FROM route_step source
         WHERE source.dataset = ?
           AND NOT EXISTS (
               SELECT 1 FROM tool target
                WHERE target.dataset = source.dataset AND target.stnfam = source.stnfam
           )
        """,
    ),
    (
        "wip_to_part",
        "wip",
        """
        SELECT COUNT(*) FROM wip source
         WHERE source.dataset = ?
           AND NOT EXISTS (
               SELECT 1 FROM part target
                WHERE target.dataset = source.dataset AND target.part = source.part
           )
        """,
    ),
    (
        "orders_to_part",
        "orders",
        """
        SELECT COUNT(*) FROM orders source
         WHERE source.dataset = ?
           AND NOT EXISTS (
               SELECT 1 FROM part target
                WHERE target.dataset = source.dataset AND target.part = source.part
           )
        """,
    ),
    (
        "wip_curstep_to_route_step",
        "wip",
        """
        SELECT COUNT(*) FROM wip source
         WHERE source.dataset = ?
           AND NOT EXISTS (
               SELECT 1
                 FROM part p
                 JOIN route_step target
                   ON target.dataset = p.dataset
                  AND target.route = p.route
                  AND target.step = source.curstep
                WHERE p.dataset = source.dataset AND p.part = source.part
           )
        """,
    ),
)


def _normalize_dataset(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in ALLOWED_DATASETS else None


def _input_validation(dataset: str) -> dict:
    with connect() as conn:
        table_counts = {
            table: conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE dataset = ?', (dataset,)
            ).fetchone()[0]
            for table in INPUT_TABLES
        }
        checks = []
        for name, source_table, unmatched_sql in RELATION_CHECKS:
            source_rows = table_counts[source_table]
            unmatched_rows = conn.execute(unmatched_sql, (dataset,)).fetchone()[0]
            checks.append(
                {
                    "check": name,
                    "source_rows": source_rows,
                    "matched_rows": source_rows - unmatched_rows,
                    "unmatched_rows": unmatched_rows,
                }
            )

    all_valid = all(check["unmatched_rows"] == 0 for check in checks)
    return {
        "status": "ok",
        "kind": "simulation",
        "simulation_type": SIMULATION_TYPE,
        "dataset": dataset,
        "scenario": f"{dataset} 입력 검증",
        "kpis": [
            {"label": "Part", "value": table_counts["part"], "unit": "개"},
            {"label": "Route Step", "value": table_counts["route_step"], "unit": "개"},
            {"label": "Tool Family", "value": table_counts["tool"], "unit": "개"},
            {"label": "초기 WIP", "value": table_counts["wip"], "unit": "lot"},
        ],
        "summary": (
            "모든 핵심 입력 관계가 유효합니다. "
            if all_valid
            else "일부 입력 관계가 끊겨 있습니다. "
        )
        + "이 결과는 실제 이산사건 시뮬레이션이 아닌 합성 mock 입력 정합성 검사입니다.",
        "table": {
            "columns": ["table", "row_count"],
            "rows": [[table, count] for table, count in table_counts.items()],
        },
        "results": checks,
    }


#: 입력 검증 결과는 그대로 표 머리글·행이 되므로 한국어 이름으로 저장한다(뜻은 시뮬레이션 output_schema와 같다).
_CHECK_COLUMNS = {
    "check": "점검 관계",
    "source_rows": "원본 건수",
    "matched_rows": "일치 건수",
    "unmatched_rows": "미일치 건수",
}
_CHECK_LABELS = {
    "part_to_route_step": "Part→Route 연결",
    "route_step_to_tool": "Route Step→설비 Family 연결",
    "wip_to_part": "초기 재공 Lot→Part 연결",
    "orders_to_part": "신규 투입 Lot→Part 연결",
    "wip_curstep_to_route_step": "재공 Lot 현재 Step→Route Step 연결",
}


def _only_failed_checks(preview: dict, columns: list[str], rows: list[list]) -> dict:
    """모델에 돌려주는 미리보기에는 미일치가 있는 점검 관계만 남긴다.

    관계 이름이 미리보기에 있으면 모두 통과해도 모델이 근거에 이름을 늘어놓았다(지침으로는 6회 중 4회).
    전체 점검 표는 `present_table`이 Result Store 에서 읽어 보여 주므로 화면에는 그대로 나온다.
    """

    unmatched = columns.index(_CHECK_COLUMNS["unmatched_rows"])
    failed = [dict(zip(columns, row)) for row in rows if row[unmatched]]
    return {
        **preview,
        "sample_rows": failed[:PREVIEW_SAMPLE_ROWS],
        "top_groups": {
            name: groups for name, groups in preview["top_groups"].items() if name != _CHECK_COLUMNS["check"]
        },
        # 통계의 최대·최소 대상 행(max_at·min_at)에도 관계 이름이 들어가므로 뺀다.
        "statistics": {
            name: {key: value for key, value in stats.items() if key not in ("max_at", "min_at")}
            for name, stats in preview["statistics"].items()
        },
        "check_summary": {"checked": len(rows), "failed": len(failed)},
    }


class MockSimulationService:
    """ProductionSimulationService와 동일한 public interface를 갖는 mock."""

    async def list_simulation(self) -> dict:
        return {"status": "ok", "simulations": list_simulation_types()}

    async def run_simulation(
        self, simulation_type: str, params: dict, *, access_scope: str | None = None
    ) -> dict:
        validation_error = validate_simulation_request(simulation_type, params)
        if validation_error is not None:
            return validation_error

        if simulation_type == PKT_SWAP_SIMULATION_TYPE:
            view = params.get("view", "all")
            if view == "by_ids" and not params.get("plan_prod_ids"):
                return {
                    "status": "missing_params",
                    "missing": [
                        {
                            "name": "plan_prod_ids",
                            "description": "view=by_ids일 때 조회할 제품 ID 목록",
                            "example": '["PROD_0001"]',
                        }
                    ],
                }
            response = generate_pkt_swap_response(
                view=view, plan_prod_ids=params.get("plan_prod_ids")
            )
            return _pkt_swap_tool_result(response, access_scope=access_scope)

        if simulation_type != SIMULATION_TYPE:
            return {
                "status": "error",
                "message": f"알 수 없는 simulation_type 입니다: {simulation_type}",
            }

        dataset = _normalize_dataset(params.get("dataset"))
        if dataset is None:
            return {
                "status": "error",
                "message": "dataset은 SEG_A 또는 SEG_B여야 합니다.",
            }

        try:
            result = _input_validation(dataset)
        except MockDbMissingError:
            return {"status": "error", "message": MISSING_DB_MESSAGE}

        records = result["results"]
        keys = list(records[0].keys())
        columns = [_CHECK_COLUMNS.get(key, key) for key in keys]
        rows = [
            [_CHECK_LABELS.get(record[key], record[key]) if key == "check" else record[key] for key in keys]
            for record in records
        ]
        meta = get_result_store().save(
            columns,
            rows,
            source=f"run_simulation:{simulation_type}",
            conversation_id=None,
            access_scope=access_scope,
        )
        preview = tool_preview(
            meta,
            pd.DataFrame(rows, columns=columns),
            kind="simulation",
            simulation_type=result["simulation_type"],
            dataset=result["dataset"],
            scenario=result["scenario"],
            summary=result["summary"],
            kpis=result["kpis"],
        )
        return _only_failed_checks(preview, columns, rows)


_service = MockSimulationService()


@logged_service_operation
async def list_simulation() -> dict:
    return await _service.list_simulation()


@logged_service_operation
async def run_simulation(
    simulation_type: str, params: dict, *, access_scope: str | None = None
) -> dict:
    return await _service.run_simulation(
        simulation_type=simulation_type, params=params, access_scope=access_scope
    )
