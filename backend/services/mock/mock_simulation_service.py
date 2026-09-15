"""Dataset-backed mock simulation service for SMT2020 input validation.

This deliberately does not claim to run a discrete-event simulation. It checks
that a selected benchmark has the input relationships a simulator would need.
"""

from __future__ import annotations

import pandas as pd

from services.mock._sqlite import MISSING_DB_MESSAGE, Smt2020DbMissingError, connect
from services.result_store import get_result_store, summarize_dataframe
from services.simulation_registry import list_simulation_types, validate_simulation_request


SIMULATION_TYPE = "SMT2020_입력검증"
ALLOWED_DATASETS = {"HVLM", "LVHM"}
INLINE_ROW_THRESHOLD = 100
SAMPLE_ROW_COUNT = 10
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
        "scenario": f"SMT2020 {dataset} 입력 검증",
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
        + "이 결과는 실제 이산사건 시뮬레이션이 아닌 SMT2020 입력 정합성 mock입니다.",
        "table": {
            "columns": ["table", "row_count"],
            "rows": [[table, count] for table, count in table_counts.items()],
        },
        "results": checks,
    }


class MockSimulationService:
    """RealSimulationService와 동일한 public interface를 갖는 mock."""

    async def list_simulation(self) -> dict:
        return {"status": "ok", "simulations": list_simulation_types()}

    async def run_simulation(
        self, simulation_type: str, params: dict, *, access_scope: str | None = None
    ) -> dict:
        error = validate_simulation_request(simulation_type, params)
        if error is not None:
            return {"status": "error", "message": error}
        if simulation_type != SIMULATION_TYPE:
            return {
                "status": "error",
                "message": f"알 수 없는 simulation_type 입니다: {simulation_type}",
            }

        dataset = _normalize_dataset(params.get("dataset"))
        if dataset is None:
            return {
                "status": "error",
                "message": "dataset은 HVLM 또는 LVHM이어야 합니다.",
            }

        try:
            result = _input_validation(dataset)
        except Smt2020DbMissingError:
            return {"status": "error", "message": MISSING_DB_MESSAGE}

        records = result["results"]
        columns = list(records[0].keys())
        rows = [[record[column] for column in columns] for record in records]
        meta = get_result_store().save(
            columns,
            rows,
            source=f"run_simulation:{simulation_type}",
            conversation_id=None,
            access_scope=access_scope,
        )
        result["result_id"] = meta.result_id
        result["columns"] = [
            {"name": column.name, "dtype": column.dtype, "role": column.role}
            for column in meta.columns
        ]
        if len(records) <= INLINE_ROW_THRESHOLD:
            result["type"] = "inline"
        else:
            result["type"] = "large_result"
            result.pop("results")
            result["sample_rows"] = rows[:SAMPLE_ROW_COUNT]
            result["note"] = result.pop("summary")
            result["summary"] = summarize_dataframe(
                pd.DataFrame(rows, columns=columns)
            )
        return result


_service = MockSimulationService()


async def list_simulation() -> dict:
    return await _service.list_simulation()


async def run_simulation(
    simulation_type: str, params: dict, *, access_scope: str | None = None
) -> dict:
    return await _service.run_simulation(
        simulation_type=simulation_type, params=params, access_scope=access_scope
    )
