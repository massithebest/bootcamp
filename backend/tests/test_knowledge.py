"""KnowledgeStore 로더/조회 계약 검증. (tmp_path 기반 최소 YAML)"""

import textwrap
from pathlib import Path

import pytest

from services.knowledge_service import KnowledgeStore


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    _write(
        tmp_path / "catalog/tables/FGS_INBOUND_RESULT.yaml",
        """
        table: FGS_INBOUND_RESULT
        description: FGS 일별 입고 실적
        grain: [work_date, line_cd]
        time_column: work_date
        tags: [실적, 입고]
        columns:
          - {name: work_date, type: date, desc: 작업일}
          - {name: line_cd, type: varchar, desc: 라인 코드, ref: LINE_MASTER.line_cd}
          - {name: status_cd, type: varchar, desc: 상태, codes: {C: 완료, X: 취소}}
        joins:
          - {to: LINE_MASTER, on: line_cd, kind: many-to-one}
        caveats: ["status_cd = 'X' 는 제외"]
        sample_sql: SELECT * FROM FGS_INBOUND_RESULT
        status: verified
        """,
    )
    _write(
        tmp_path / "catalog/tables/LINE_MASTER.yaml",
        """
        table: LINE_MASTER
        description: 생산 라인 마스터
        grain: [line_cd]
        tags: [마스터]
        columns:
          - {name: line_cd, type: varchar, desc: 라인 코드}
        status: draft
        """,
    )
    _write(
        tmp_path / "kpi/fgs_inbound.yaml",
        """
        kpi_id: fgs_inbound
        name: FGS 입고 실적
        aliases: [입고 실적]
        definition: 기간 내 입고 완료 수량
        formula: SUM(inbound_qty)
        sources: [FGS_INBOUND_RESULT]
        grain: [work_date]
        baseline: PRODUCTION_PLAN.plan_qty
        shortfall_rule: 달성률 < 0.9 이면 부진
        sql_template: SELECT 1 FROM FGS_INBOUND_RESULT
        diagnostics:
          - {hypothesis: 자재 결품, how: sql, ref: MATERIAL_SHORTAGE}
        status: draft
        """,
    )
    _write(
        tmp_path / "simulations/MP_확정조회.yaml",
        """
        type: MP_확정조회
        name: 확정 MP 조회
        aliases: [확정 MP]
        when_to_use: 계획 변경 확인
        params:
          fixedPlanMonth: {required: false, description: 조회 연월, example: "202609"}
        output_schema:
          mpVersion: {type: string, desc: 버전}
        status: verified
        """,
    )
    _write(
        tmp_path / "glossary.yaml",
        """
        - term: FGS
          definition: 완제품 창고
          aliases: [완제품 창고]
          related_kpis: [fgs_inbound]
          related_tables: [FGS_INBOUND_RESULT]
          status: draft
        """,
    )
    _write(
        tmp_path / "recipes/plan_vs_actual.yaml",
        """
        recipe_id: plan_vs_actual
        name: 계획 대비 실적
        description: FGS 입고 실적과 라인 마스터를 조인해 라인별로 집계하는 CTE
        cte_name: plan_vs_actual
        cte_sql: |
          SELECT r.work_date, r.line_cd, SUM(1) AS cnt
          FROM FGS_INBOUND_RESULT r
          JOIN LINE_MASTER l ON l.line_cd = r.line_cd
          GROUP BY r.work_date, r.line_cd
        sources: [FGS_INBOUND_RESULT, LINE_MASTER]
        sample_queries:
          - description: 라인별 합계
            sql: SELECT line_cd, SUM(cnt) FROM plan_vs_actual GROUP BY line_cd
        status: draft
        """,
    )
    return tmp_path


def test_load_reads_all_kinds(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert len(store.list_tables()) == 2
    assert len(store.list_kpis()) == 1
    assert len(store.list_simulations()) == 1
    assert len(store.list_recipes()) == 1
    assert store.table_names() == {"FGS_INBOUND_RESULT", "LINE_MASTER"}


def test_invalid_yaml_error_includes_filename(root: Path) -> None:
    _write(root / "catalog/tables/BROKEN.yaml", "table: BROKEN\n")  # description 등 누락

    with pytest.raises(ValueError) as excinfo:
        KnowledgeStore.load(root)

    assert "BROKEN.yaml" in str(excinfo.value)


def test_list_tables_keyword_and_tag_filter(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [t["table"] for t in store.list_tables(keyword="입고")] == ["FGS_INBOUND_RESULT"]
    # 컬럼명 부분일치
    assert [t["table"] for t in store.list_tables(keyword="status_cd")] == ["FGS_INBOUND_RESULT"]
    assert [t["table"] for t in store.list_tables(tag="마스터")] == ["LINE_MASTER"]
    assert store.list_tables(keyword="존재하지않는") == []


def test_list_tables_summary_shape(root: Path) -> None:
    (row,) = store_rows = [
        t for t in KnowledgeStore.load(root).list_tables(tag="실적")
    ]
    assert set(row) == {"table", "description", "grain", "tags", "verified"}
    assert store_rows[0]["verified"] is True


def test_describe_table_full_and_verified(root: Path) -> None:
    store = KnowledgeStore.load(root)

    described = store.describe_table("FGS_INBOUND_RESULT")
    assert described["verified"] is True
    assert described["caveats"] == ["status_cd = 'X' 는 제외"]
    assert described["columns"][2]["codes"] == {"C": "완료", "X": "취소"}

    assert store.describe_table("LINE_MASTER")["verified"] is False


def test_describe_table_unknown_returns_error(root: Path) -> None:
    result = KnowledgeStore.load(root).describe_table("NO_SUCH")

    assert result["status"] == "error"
    assert "NO_SUCH" in result["message"]
    assert "list_tables" in result["message"]


def test_list_kpis_keyword_matches_alias(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [k["kpi_id"] for k in store.list_kpis(keyword="입고 실적")] == ["fgs_inbound"]
    assert set(store.list_kpis()[0]) == {"kpi_id", "name", "aliases", "verified"}


def test_get_kpi_full_and_unknown(root: Path) -> None:
    store = KnowledgeStore.load(root)

    kpi = store.get_kpi("fgs_inbound")
    assert kpi["shortfall_rule"].startswith("달성률")
    assert kpi["diagnostics"][0]["how"] == "sql"
    assert kpi["verified"] is False

    error = store.get_kpi("no_such")
    assert error["status"] == "error"
    assert "list_kpis" in error["message"]


def test_get_simulation_merges_params(root: Path) -> None:
    store = KnowledgeStore.load(root)

    sim = store.get_simulation("MP_확정조회")
    assert sim["params"]["fixedPlanMonth"]["required"] is False
    assert sim["verified"] is True
    assert store.get_simulation("없음")["status"] == "error"


def test_glossary_loaded(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [g["term"] for g in store.list_glossary()] == ["FGS"]


def test_missing_directory_loads_empty(tmp_path: Path) -> None:
    store = KnowledgeStore.load(tmp_path / "nope")

    assert store.list_tables() == []
    assert store.table_names() == set()
    assert store.list_recipes() == []


def test_list_recipes_keyword_filter(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [r["recipe_id"] for r in store.list_recipes(keyword="계획 대비")] == [
        "plan_vs_actual"
    ]
    assert set(store.list_recipes()[0]) == {
        "recipe_id",
        "name",
        "description",
        "cte_name",
        "verified",
    }
    assert store.list_recipes(keyword="존재하지않는") == []


def test_get_recipe_full_and_verified(root: Path) -> None:
    store = KnowledgeStore.load(root)

    recipe = store.get_recipe("plan_vs_actual")
    assert recipe["cte_name"] == "plan_vs_actual"
    assert recipe["sources"] == ["FGS_INBOUND_RESULT", "LINE_MASTER"]
    assert recipe["sample_queries"][0]["description"] == "라인별 합계"
    assert recipe["verified"] is False


def test_get_recipe_unknown_returns_error(root: Path) -> None:
    result = KnowledgeStore.load(root).get_recipe("no_such")

    assert result["status"] == "error"
    assert "no_such" in result["message"]
    assert "list_recipes" in result["message"]
