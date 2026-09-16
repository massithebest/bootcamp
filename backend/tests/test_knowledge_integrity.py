"""실제 `knowledge/` 디렉터리의 정합성 검사. (설계 §6 "정합성 검사")

지식은 개발 중 계속 늘어난다. 여기서 막는 것은 서로를 가리키는 참조가
끊기는 경우 — 카탈로그에 없는 테이블을 KPI 가 원천으로 적거나,
diagnostics 가 존재하지 않는 시뮬레이션을 가리키는 상황이다.
"""

import re

import pytest

from core.config import KNOWLEDGE_DIR
from services.knowledge_service import KnowledgeStore


@pytest.fixture(scope="module")
def store() -> KnowledgeStore:
    return KnowledgeStore.load(KNOWLEDGE_DIR)


#: `FROM`/`JOIN` 뒤의 이름. `services/sql_guard.py`의 `_TABLE_REF`와 같은 패턴.
#: `(?<![:\w.])` 는 `BETWEEN :from AND :to` 의 `:from` 을 FROM 절로 오인하지
#: 않게 한다.
_TABLE_REF = re.compile(r"(?<![:\w.])\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)


def _referenced_tables(sql: str) -> set[str]:
    return {name.upper() for name in _TABLE_REF.findall(sql)}


def _table_columns(store: KnowledgeStore, table: str) -> set[str]:
    return {column.name for column in store.tables[table].columns}


def test_all_yaml_loads(store: KnowledgeStore) -> None:
    assert store.tables, "카탈로그 테이블이 하나도 로드되지 않았다"
    assert store.kpis, "KPI 가 하나도 로드되지 않았다"


def test_tables_and_recipes_have_query_guidance(store: KnowledgeStore) -> None:
    for table in store.tables.values():
        assert table.query_rules, f"테이블 {table.table} 에 query_rules가 없다"
        assert table.visualization_hints, (
            f"테이블 {table.table} 에 visualization_hints가 없다"
        )
        assert all(
            set(sample.model_dump()) == {"question", "sql"}
            for sample in table.sample_queries
        )
    for recipe in store.recipes.values():
        assert recipe.query_rules, f"레시피 {recipe.recipe_id} 에 query_rules가 없다"
        assert all(
            set(sample.model_dump()) == {"question", "sql"}
            for sample in recipe.sample_queries
        )


def test_column_refs_point_to_existing_table_column(store: KnowledgeStore) -> None:
    for table in store.tables.values():
        for column in table.columns:
            if column.ref is None:
                continue
            assert re.fullmatch(r"\w+\.\w+", column.ref), (
                f"{table.table}.{column.name}.ref 는 TABLE.column 형태여야 한다: {column.ref}"
            )
            target_table, target_column = column.ref.split(".")
            assert target_table in store.tables, (
                f"{table.table}.{column.name} 이 없는 테이블을 참조: {target_table}"
            )
            assert target_column in _table_columns(store, target_table), (
                f"{table.table}.{column.name} 이 없는 컬럼을 참조: {column.ref}"
            )


def test_joins_point_to_existing_tables(store: KnowledgeStore) -> None:
    for table in store.tables.values():
        for join in table.joins:
            assert join.to in store.tables, f"{table.table} 의 join 대상이 없다: {join.to}"


def test_kpi_sources_exist(store: KnowledgeStore) -> None:
    for kpi in store.kpis.values():
        for source in kpi.sources:
            assert source in store.tables, f"KPI {kpi.kpi_id} 의 원천 테이블이 없다: {source}"


def test_kpi_recipe_references_resolve(store: KnowledgeStore) -> None:
    for kpi in store.kpis.values():
        for ref in kpi.recipe_refs:
            assert ref in store.recipes, f"KPI {kpi.kpi_id} 의 레시피가 없다: {ref}"


def test_kpi_sql_template_tables_are_declared_sources(store: KnowledgeStore) -> None:
    for kpi in store.kpis.values():
        used = _referenced_tables(kpi.sql_template)
        declared = {source.upper() for source in kpi.sources}
        assert used <= declared, (
            f"KPI {kpi.kpi_id} 의 sql_template 이 sources 에 없는 테이블을 쓴다: {used - declared}"
        )


def test_diagnostics_refs_resolve(store: KnowledgeStore) -> None:
    for kpi in store.kpis.values():
        for diagnostic in kpi.diagnostics:
            ref = diagnostic.ref
            if diagnostic.how == "simulation":
                if not store.simulations:
                    pytest.skip("simulations/ 가 비어 있다 (Task 6 이전)")
                assert ref in store.simulations, (
                    f"KPI {kpi.kpi_id} diagnostics 가 없는 시뮬레이션을 가리킨다: {ref}"
                )
            else:
                is_table = ref in store.tables
                # recipes/<recipe_id> 형태 — 레시피는 knowledge/recipes/*.yaml 로 로드되므로
                # store.recipes 에서 확인한다 (파일시스템의 .md 를 직접 찾지 않는다).
                is_recipe = ref.startswith("recipes/") and (
                    ref.removeprefix("recipes/") in store.recipes
                )
                assert is_table or is_recipe, (
                    f"KPI {kpi.kpi_id} diagnostics 가 테이블도 레시피도 아닌 것을 가리킨다: {ref}"
                )


def test_recipe_sources_exist(store: KnowledgeStore) -> None:
    for recipe in store.recipes.values():
        for source in recipe.sources:
            assert source in store.tables, (
                f"레시피 {recipe.recipe_id} 의 원천 테이블이 없다: {source}"
            )


def test_recipe_cte_sql_tables_are_declared_sources(store: KnowledgeStore) -> None:
    for recipe in store.recipes.values():
        used = _referenced_tables(recipe.cte_sql)
        declared = {source.upper() for source in recipe.sources}
        assert used <= declared, (
            f"레시피 {recipe.recipe_id} 의 cte_sql 이 sources 에 없는 테이블을 쓴다: "
            f"{used - declared}"
        )


def test_recipe_sample_queries_reference_declared_or_own_cte(store: KnowledgeStore) -> None:
    for recipe in store.recipes.values():
        # 샘플 쿼리는 CTE 자기 자신(cte_name)을 FROM 하는 게 정상이므로 허용 목록에 포함한다.
        allowed = {source.upper() for source in recipe.sources} | {recipe.cte_name.upper()}
        for sample in recipe.sample_queries:
            used = _referenced_tables(sample.sql)
            assert used <= allowed, (
                f"레시피 {recipe.recipe_id} 의 샘플 쿼리가 선언되지 않은 대상을 쓴다: "
                f"{used - allowed} (질문: {sample.question})"
            )


def test_table_sample_queries_reference_own_table(store: KnowledgeStore) -> None:
    for table in store.tables.values():
        for sample in table.sample_queries:
            used = _referenced_tables(sample.sql)
            assert used <= {table.table.upper()}, (
                f"테이블 {table.table} 의 샘플 쿼리가 다른 테이블을 쓴다: "
                f"{used - {table.table.upper()}} (질문: {sample.question})"
            )


def test_scenario_references_resolve(store: KnowledgeStore) -> None:
    for scenario in store.scenarios.values():
        for step in scenario.steps:
            if step.action == "recipe":
                assert step.ref in store.recipes, (
                    f"시나리오 {scenario.scenario_id}가 없는 recipe를 참조: {step.ref}"
                )
            else:
                assert step.ref in store.simulations, (
                    f"시나리오 {scenario.scenario_id}가 없는 simulation을 참조: {step.ref}"
                )
        for table, count in scenario.expected.table_counts.items():
            assert table in store.tables, (
                f"시나리오 {scenario.scenario_id}가 없는 테이블을 참조: {table}"
            )
            assert count >= 0
        assert all(count >= 0 for count in scenario.expected.unmatched_rows.values())


def test_glossary_links_resolve(store: KnowledgeStore) -> None:
    for entry in store.glossary:
        for table in entry.related_tables:
            assert table in store.tables, f"용어 {entry.term} 이 없는 테이블을 참조: {table}"
        for kpi_id in entry.related_kpis:
            assert kpi_id in store.kpis, f"용어 {entry.term} 이 없는 KPI 를 참조: {kpi_id}"
