"""aggregate_result: 저장 결과를 기준별로 서버에서 다시 집계한다."""

import asyncio
import json

import pytest

from services.results import store as result_store
from services.results.store import LocalParquetResultStore
from tools.result_tool import aggregate_result


SWAP_ROWS = [
    ["PROD_0001", "GIVE", 158.2],
    ["PROD_0001", "RECEIVE", 158.2],
    ["PROD_0009", "GIVE", 712.5],
    ["PROD_0009", "GIVE", 586.8],
    ["PROD_0009", "RECEIVE", 586.8],
    ["PROD_0010", None, None],
]


@pytest.fixture
def store(tmp_path, monkeypatch):
    local = LocalParquetResultStore(tmp_path)
    monkeypatch.setattr(result_store, "_store", local)
    return local


def _saved(store, scope="scope-a"):
    return store.save(
        ["planProductId", "swap_direction", "swap_swapQty"],
        SWAP_ROWS,
        source="run_simulation:PKT_목표수량_스왑산출",
        conversation_id=None,
        access_scope=scope,
    )


def test_aggregate_sums_by_group_into_a_new_labelled_result(store) -> None:
    meta = _saved(store)

    result = asyncio.run(
        aggregate_result(
            meta.result_id,
            ["swap_direction"],
            "swap_swapQty",
            "sum",
            {"swap_direction": "Swap 방향", "swap_swapQty": "Swap 수량 합계"},
            access_scope="scope-a",
        )
    )

    assert result["status"] == "ok"
    assert result["result_id"] != meta.result_id
    assert result["source_result_id"] == meta.result_id and result["source_row_count"] == 6
    assert result["excluded_blank_group_rows"] == 1
    assert [c["name"] for c in result["columns"]] == ["Swap 방향", "Swap 수량 합계"]
    frame = store.load(result["result_id"])
    assert frame.values.tolist() == [["GIVE", 1457.5], ["RECEIVE", 745.0]]
    assert store.get_meta(result["result_id"]).access_scope == "scope-a"
    # 원본 결과는 바뀌지 않는다.
    assert len(store.load(meta.result_id)) == 6


def test_aggregate_count_and_default_value_label(store) -> None:
    meta = _saved(store)

    result = asyncio.run(
        aggregate_result(meta.result_id, ["planProductId", "swap_direction"], "swap_swapQty", "count", access_scope="scope-a")
    )

    assert result["status"] == "ok"
    frame = store.load(result["result_id"])
    assert list(frame.columns) == ["planProductId", "swap_direction", "swap_swapQty 건수"]
    assert frame.values.tolist() == [
        ["PROD_0001", "GIVE", 1], ["PROD_0001", "RECEIVE", 1],
        ["PROD_0009", "GIVE", 2], ["PROD_0009", "RECEIVE", 1],
    ]


@pytest.mark.parametrize(
    ("group_by", "value_column", "aggregation", "labels", "message"),
    [
        (["missing"], "swap_swapQty", "sum", None, "결과에 없는 컬럼"),
        (["swap_direction"], "swap_direction", "sum", None, "group_by에 넣을 수 없습니다"),
        (["swap_direction"], "planProductId", "sum", None, "숫자 값이 없습니다"),
        (["swap_direction"], "swap_swapQty", "median", None, "aggregation은"),
        (["swap_direction"], "swap_swapQty", "sum", {"swap_direction": "값", "swap_swapQty": "값"}, "겹칩니다"),
    ],
)
def test_aggregate_rejects_invalid_requests(store, group_by, value_column, aggregation, labels, message) -> None:
    meta = _saved(store)

    result = asyncio.run(
        aggregate_result(meta.result_id, group_by, value_column, aggregation, labels, access_scope="scope-a")
    )

    assert result["status"] == "error" and message in result["message"]


def test_aggregate_hides_results_from_other_scopes(store, tmp_path) -> None:
    meta = _saved(store, scope="scope-a")

    result = asyncio.run(
        aggregate_result(meta.result_id, ["swap_direction"], "swap_swapQty", "sum", access_scope="scope-b")
    )

    assert result["status"] == "error"
    assert str(tmp_path) not in json.dumps(result, ensure_ascii=False)
    assert len(list(tmp_path.glob("*.parquet"))) == 1


def test_aggregate_rejects_sql_results(store) -> None:
    meta = store.save(["FAC_ID", "qty"], [["FAC001", 1]], source="execute_sql", conversation_id=None, access_scope="scope-a")

    result = asyncio.run(aggregate_result(meta.result_id, ["FAC_ID"], "qty", "sum", access_scope="scope-a"))

    assert result["status"] == "error" and "GROUP BY" in result["message"]


def test_aggregate_sums_extra_value_columns_in_one_result(store) -> None:
    # 사이트별 계획·목표수량을 한 표로 보려고 결과 행을 SQL 리터럴로 옮겨 적어 합산했다(2026-11-04).
    meta = store.save(
        ["사이트", "계획수량", "목표수량"],
        [["SITE_A", 100, 10.5], ["SITE_A", 50, -2.5], ["SITE_B", 70, 7.0]],
        source="run_simulation:PKT_목표수량_스왑산출",
        conversation_id=None,
        access_scope="scope-a",
    )

    result = asyncio.run(
        aggregate_result(
            meta.result_id, ["사이트"], "계획수량", "sum", {"계획수량": "계획수량 합계"},
            extra_value_columns=["목표수량"], access_scope="scope-a",
        )
    )

    assert result["status"] == "ok"
    assert [c["name"] for c in result["columns"]] == ["사이트", "계획수량 합계", "목표수량 합계"]
    assert store.load(result["result_id"]).values.tolist() == [["SITE_A", 150, 8.0], ["SITE_B", 70, 7.0]]
    duplicate = asyncio.run(
        aggregate_result(meta.result_id, ["사이트"], "계획수량", "sum", extra_value_columns=["계획수량"], access_scope="scope-a")
    )
    assert duplicate["status"] == "error" and "겹칩니다" in duplicate["message"]
