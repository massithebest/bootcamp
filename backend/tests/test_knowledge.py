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
        tmp_path / "catalog/tables/wip.yaml",
        """
        table: wip
        description: SMT2020 초기 재공
        grain: [dataset, lot]
        time_column: due
        tags: [WIP, 재공]
        columns:
          - {name: dataset, type: varchar, desc: 데이터셋}
          - {name: lot, type: varchar, desc: Lot ID}
          - {name: part, type: varchar, desc: Part ID, ref: part.part}
        joins:
          - {to: part, on: [dataset, part], kind: many-to-one}
        caveats: ["JOIN에 dataset을 포함"]
        query_rules: ["dataset을 필수로 제한"]
        visualization_hints: ["Part별 비교는 bar 차트"]
        sample_queries:
          - question: WIP 원본을 보여줘
            sql: SELECT * FROM wip
        status: verified
        """,
    )
    _write(
        tmp_path / "catalog/tables/part.yaml",
        """
        table: part
        description: Part 마스터
        grain: [dataset, part]
        tags: [마스터]
        columns:
          - {name: dataset, type: varchar, desc: 데이터셋}
          - {name: part, type: varchar, desc: Part ID}
        status: draft
        """,
    )
    _write(
        tmp_path / "kpi/initial_wip.yaml",
        """
        kpi_id: initial_wip
        name: 초기 WIP
        aliases: [재공]
        definition: 초기 재공 Lot 수
        formula: COUNT(*)
        sources: [wip]
        grain: [dataset, part]
        baseline: wip 원본
        shortfall_rule: 부족 판정 없음
        sql_template: SELECT 1 FROM wip
        diagnostics:
          - {hypothesis: Route 연결, how: sql, ref: part}
        status: draft
        """,
    )
    _write(
        tmp_path / "simulations/SMT2020_입력검증.yaml",
        """
        type: SMT2020_입력검증
        name: 입력 검증
        aliases: [정합성 검증]
        when_to_use: simulation 입력 확인
        params:
          dataset: {required: true, description: 데이터셋, example: LVHM}
        output_schema:
          results: {type: array, desc: 관계 검사}
        status: verified
        """,
    )
    _write(
        tmp_path / "glossary.yaml",
        """
        - term: WIP
          definition: 초기 재공
          aliases: [재공]
          related_kpis: [initial_wip]
          related_tables: [wip]
          status: draft
        """,
    )
    _write(
        tmp_path / "recipes/wip_by_part.yaml",
        """
        recipe_id: wip_by_part
        name: Part별 WIP
        description: WIP와 Part 마스터를 dataset과 part로 조인하는 CTE
        cte_name: wip_by_part
        cte_sql: |
          SELECT w.dataset, w.part, COUNT(*) AS cnt
          FROM wip w
          JOIN part p ON p.dataset = w.dataset AND p.part = w.part
          GROUP BY w.dataset, w.part
        sources: [wip, part]
        query_rules: ["dataset을 필수로 제한"]
        sample_queries:
          - question: 데이터셋별 WIP 합계는?
            sql: SELECT dataset, SUM(cnt) FROM wip_by_part GROUP BY dataset
        status: draft
        """,
    )
    _write(
        tmp_path / "scenarios/lvhm_input_integrity.yaml",
        """
        scenario_id: lvhm_input_integrity
        name: LVHM 입력 검증
        description: recipe와 simulation을 함께 확인
        dataset: LVHM
        question: LVHM WIP와 Route 관계를 검증해줘
        steps:
          - action: recipe
            ref: wip_by_part
            params: {dataset: LVHM}
            expectation: Part별 WIP가 조회된다
          - action: simulation
            ref: SMT2020_입력검증
            params: {dataset: LVHM}
            expectation: unmatched가 0이다
        expected:
          table_counts: {part: 10, wip: 2156}
          unmatched_rows: {wip_to_part: 0}
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
    assert len(store.list_scenarios()) == 1
    assert store.table_names() == {"wip", "part"}


def test_invalid_yaml_error_includes_filename(root: Path) -> None:
    _write(root / "catalog/tables/BROKEN.yaml", "table: BROKEN\n")  # description 등 누락

    with pytest.raises(ValueError) as excinfo:
        KnowledgeStore.load(root)

    assert "BROKEN.yaml" in str(excinfo.value)


def test_list_tables_keyword_and_tag_filter(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [t["table"] for t in store.list_tables(keyword="재공")] == ["wip"]
    # 컬럼명 부분일치
    assert [t["table"] for t in store.list_tables(keyword="lot")] == ["wip"]
    assert [t["table"] for t in store.list_tables(tag="마스터")] == ["part"]
    assert store.list_tables(keyword="존재하지않는") == []


def test_list_tables_summary_shape(root: Path) -> None:
    (row,) = store_rows = [
        t for t in KnowledgeStore.load(root).list_tables(tag="WIP")
    ]
    assert set(row) == {"table", "description", "grain", "tags", "verified"}
    assert store_rows[0]["verified"] is True


def test_describe_table_full_and_verified(root: Path) -> None:
    store = KnowledgeStore.load(root)

    described = store.describe_table("wip")
    assert described["verified"] is True
    assert described["caveats"] == ["JOIN에 dataset을 포함"]
    assert described["query_rules"] == ["dataset을 필수로 제한"]
    assert described["visualization_hints"] == ["Part별 비교는 bar 차트"]
    assert described["columns"][2]["ref"] == "part.part"
    assert set(described["sample_queries"][0]) == {"question", "sql"}

    assert store.describe_table("part")["verified"] is False


def test_describe_table_unknown_returns_error(root: Path) -> None:
    result = KnowledgeStore.load(root).describe_table("NO_SUCH")

    assert result["status"] == "error"
    assert "NO_SUCH" in result["message"]
    assert "list_tables" in result["message"]


def test_list_kpis_keyword_matches_alias(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [k["kpi_id"] for k in store.list_kpis(keyword="재공")] == ["initial_wip"]
    assert set(store.list_kpis()[0]) == {"kpi_id", "name", "aliases", "verified"}


def test_get_kpi_full_and_unknown(root: Path) -> None:
    store = KnowledgeStore.load(root)

    kpi = store.get_kpi("initial_wip")
    assert kpi["shortfall_rule"].startswith("부족")
    assert kpi["diagnostics"][0]["how"] == "sql"
    assert kpi["verified"] is False

    error = store.get_kpi("no_such")
    assert error["status"] == "error"
    assert "list_kpis" in error["message"]


def test_get_simulation_merges_params(root: Path) -> None:
    store = KnowledgeStore.load(root)

    sim = store.get_simulation("SMT2020_입력검증")
    assert sim["params"]["dataset"]["required"] is True
    assert sim["verified"] is True
    assert store.get_simulation("없음")["status"] == "error"


def test_glossary_loaded(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [g["term"] for g in store.list_glossary()] == ["WIP"]


def test_missing_directory_loads_empty(tmp_path: Path) -> None:
    store = KnowledgeStore.load(tmp_path / "nope")

    assert store.list_tables() == []
    assert store.table_names() == set()
    assert store.list_recipes() == []
    assert store.list_scenarios() == []


def test_list_recipes_keyword_filter(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [r["recipe_id"] for r in store.list_recipes(keyword="Part별")] == [
        "wip_by_part"
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

    recipe = store.get_recipe("wip_by_part")
    assert recipe["cte_name"] == "wip_by_part"
    assert recipe["sources"] == ["wip", "part"]
    assert recipe["query_rules"] == ["dataset을 필수로 제한"]
    assert recipe["sample_queries"][0]["question"] == "데이터셋별 WIP 합계는?"
    assert set(recipe["sample_queries"][0]) == {"question", "sql"}
    assert recipe["verified"] is False


def test_get_recipe_unknown_returns_error(root: Path) -> None:
    result = KnowledgeStore.load(root).get_recipe("no_such")

    assert result["status"] == "error"
    assert "no_such" in result["message"]
    assert "list_recipes" in result["message"]


def test_list_and_get_scenarios(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert [row["scenario_id"] for row in store.list_scenarios("LVHM")] == [
        "lvhm_input_integrity"
    ]
    assert store.list_scenarios("존재하지않는") == []
    scenario = store.get_scenario("LVHM_INPUT_INTEGRITY")
    assert scenario["dataset"] == "LVHM"
    assert scenario["steps"][0]["ref"] == "wip_by_part"
    assert scenario["expected"]["table_counts"]["wip"] == 2156
    assert scenario["verified"] is False


def test_get_scenario_unknown_returns_error(root: Path) -> None:
    result = KnowledgeStore.load(root).get_scenario("no_such")

    assert result["status"] == "error"
    assert "list_scenarios" in result["message"]


def test_legacy_yaml_without_aggregation_guide_still_loads(root: Path) -> None:
    store = KnowledgeStore.load(root)

    assert store.describe_table("wip")["aggregation_rules"] == []
    assert store.get_kpi("initial_wip")["recipe_refs"] == []
    recipe = store.get_recipe("wip_by_part")
    assert recipe["output_grain"] == []
    assert recipe["output_columns"] == []
    assert recipe["aggregation_rules"] == []


def test_sample_query_rejects_removed_answer_field(root: Path) -> None:
    _write(
        root / "catalog/tables/invalid_sample.yaml",
        "table: invalid_sample\ndescription: invalid\ngrain: [id]\n"
        "columns: [{name: id, type: int}]\nsample_queries:\n"
        "  - question: invalid\n    sql: SELECT * FROM invalid_sample\n"
        "    answer: 더 이상 허용하지 않는 필드\n",
    )

    with pytest.raises(ValueError, match="invalid_sample.yaml"):
        KnowledgeStore.load(root)


@pytest.mark.parametrize(
    "guide",
    [
        "output_grain: [missing]\noutput_columns: [{name: qty, role: measure}]",
        "output_grain: [qty]",
        "output_columns: [{name: qty, role: measure}, {name: qty, role: measure}]",
        "output_columns: [{name: qty, role: invalid}]",
        "aggregation_rules: SUM(qty)",
    ],
)
def test_invalid_recipe_guide_reports_filename(root: Path, guide: str) -> None:
    _write(
        root / "recipes/invalid.yaml",
        "recipe_id: invalid\nname: invalid\ndescription: invalid\n"
        "cte_name: invalid\ncte_sql: SELECT 1 AS qty\nsources: []\n" + guide,
    )

    with pytest.raises(ValueError, match="invalid.yaml"):
        KnowledgeStore.load(root)
