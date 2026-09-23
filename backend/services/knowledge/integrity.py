"""지식 항목 사이의 참조 정합성 검사.

`tests/test_knowledge_integrity.py`와 변경 요청 승인 게이트가 같은 규칙을 쓴다.
검사는 저장소를 읽기만 하며 각 규칙은 사람이 읽을 수 있는 문제 문장 목록을 돌려준다.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from services.knowledge.catalog import KnowledgeStore

#: `FROM`/`JOIN` 뒤의 이름. `services/sql/guard.py`의 `_TABLE_REF`와 같은 패턴.
#: `(?<![:\w.])` 는 `BETWEEN :from AND :to` 의 `:from` 을 FROM 절로 오인하지 않게 한다.
_TABLE_REF = re.compile(r"(?<![:\w.])\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)


def _referenced_tables(sql: str) -> set[str]:
    return {name.upper() for name in _TABLE_REF.findall(sql)}


def _table_columns(store: KnowledgeStore, table: str) -> set[str]:
    return {column.name for column in store.tables[table].columns}


def check_query_guidance(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for table in store.tables.values():
        if not table.query_rules:
            issues.append(f"테이블 {table.table} 에 query_rules가 없다")
        if not table.visualization_hints:
            issues.append(f"테이블 {table.table} 에 visualization_hints가 없다")
    for recipe in store.recipes.values():
        if not recipe.query_rules:
            issues.append(f"레시피 {recipe.recipe_id} 에 query_rules가 없다")
    return issues


def check_column_refs(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for table in store.tables.values():
        for column in table.columns:
            if column.ref is None:
                continue
            label = f"{table.table}.{column.name}"
            if not re.fullmatch(r"\w+\.\w+", column.ref):
                issues.append(f"{label}.ref 는 TABLE.column 형태여야 한다: {column.ref}")
                continue
            target_table, target_column = column.ref.split(".")
            if target_table not in store.tables:
                issues.append(f"{label} 이 없는 테이블을 참조: {target_table}")
            elif target_column not in _table_columns(store, target_table):
                issues.append(f"{label} 이 없는 컬럼을 참조: {column.ref}")
    return issues


def check_joins(store: KnowledgeStore) -> list[str]:
    return [
        f"{table.table} 의 join 대상이 없다: {join.to}"
        for table in store.tables.values()
        for join in table.joins
        if join.to not in store.tables
    ]


def check_kpi_sources(store: KnowledgeStore) -> list[str]:
    return [
        f"KPI {kpi.kpi_id} 의 원천 테이블이 없다: {source}"
        for kpi in store.kpis.values()
        for source in kpi.sources
        if source not in store.tables
    ]


def check_kpi_recipe_refs(store: KnowledgeStore) -> list[str]:
    return [
        f"KPI {kpi.kpi_id} 의 레시피가 없다: {ref}"
        for kpi in store.kpis.values()
        for ref in kpi.recipe_refs
        if ref not in store.recipes
    ]


def check_kpi_sql_template(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for kpi in store.kpis.values():
        undeclared = _referenced_tables(kpi.sql_template) - {s.upper() for s in kpi.sources}
        if undeclared:
            issues.append(
                f"KPI {kpi.kpi_id} 의 sql_template 이 sources 에 없는 테이블을 쓴다: "
                f"{sorted(undeclared)}"
            )
    return issues


def check_diagnostics(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for kpi in store.kpis.values():
        for diagnostic in kpi.diagnostics:
            ref = diagnostic.ref
            if diagnostic.how == "simulation":
                if ref not in store.simulations:
                    issues.append(
                        f"KPI {kpi.kpi_id} diagnostics 가 없는 시뮬레이션을 가리킨다: {ref}"
                    )
                continue
            is_table = ref in store.tables
            is_recipe = ref.startswith("recipes/") and (
                ref.removeprefix("recipes/") in store.recipes
            )
            if not (is_table or is_recipe):
                issues.append(
                    f"KPI {kpi.kpi_id} diagnostics 가 테이블도 레시피도 아닌 것을 가리킨다: {ref}"
                )
    return issues


def check_recipe_sources(store: KnowledgeStore) -> list[str]:
    return [
        f"레시피 {recipe.recipe_id} 의 원천 테이블이 없다: {source}"
        for recipe in store.recipes.values()
        for source in recipe.sources
        if source not in store.tables
    ]


def check_recipe_cte_sql(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for recipe in store.recipes.values():
        undeclared = _referenced_tables(recipe.cte_sql) - {s.upper() for s in recipe.sources}
        if undeclared:
            issues.append(
                f"레시피 {recipe.recipe_id} 의 cte_sql 이 sources 에 없는 테이블을 쓴다: "
                f"{sorted(undeclared)}"
            )
    return issues


def check_recipe_sample_queries(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for recipe in store.recipes.values():
        # 샘플 쿼리는 CTE 자기 자신(cte_name)을 FROM 하는 게 정상이므로 허용 목록에 포함한다.
        allowed = {s.upper() for s in recipe.sources} | {recipe.cte_name.upper()}
        for sample in recipe.sample_queries:
            undeclared = _referenced_tables(sample.sql) - allowed
            if undeclared:
                issues.append(
                    f"레시피 {recipe.recipe_id} 의 샘플 쿼리가 선언되지 않은 대상을 쓴다: "
                    f"{sorted(undeclared)} (질문: {sample.question})"
                )
    return issues


def check_table_sample_queries(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for table in store.tables.values():
        for sample in table.sample_queries:
            undeclared = _referenced_tables(sample.sql) - {table.table.upper()}
            if undeclared:
                issues.append(
                    f"테이블 {table.table} 의 샘플 쿼리가 다른 테이블을 쓴다: "
                    f"{sorted(undeclared)} (질문: {sample.question})"
                )
    return issues


def check_scenario_refs(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for scenario in store.scenarios.values():
        for step in scenario.steps:
            known = store.recipes if step.action == "recipe" else store.simulations
            if step.ref not in known:
                issues.append(
                    f"시나리오 {scenario.scenario_id}가 없는 {step.action}을 참조: {step.ref}"
                )
        for table, count in scenario.expected.table_counts.items():
            if table not in store.tables:
                issues.append(f"시나리오 {scenario.scenario_id}가 없는 테이블을 참조: {table}")
            if count < 0:
                issues.append(f"시나리오 {scenario.scenario_id}의 table_counts 가 음수다: {table}")
        if any(count < 0 for count in scenario.expected.unmatched_rows.values()):
            issues.append(f"시나리오 {scenario.scenario_id}의 unmatched_rows 가 음수다")
    return issues


def check_glossary_links(store: KnowledgeStore) -> list[str]:
    issues: list[str] = []
    for entry in store.glossary:
        for table in entry.related_tables:
            if table not in store.tables:
                issues.append(f"용어 {entry.term} 이 없는 테이블을 참조: {table}")
        for kpi_id in entry.related_kpis:
            if kpi_id not in store.kpis:
                issues.append(f"용어 {entry.term} 이 없는 KPI 를 참조: {kpi_id}")
    return issues


CHECKS: dict[str, Callable[[KnowledgeStore], list[str]]] = {
    "query_guidance": check_query_guidance,
    "column_refs": check_column_refs,
    "joins": check_joins,
    "kpi_sources": check_kpi_sources,
    "kpi_recipe_refs": check_kpi_recipe_refs,
    "kpi_sql_template": check_kpi_sql_template,
    "diagnostics": check_diagnostics,
    "recipe_sources": check_recipe_sources,
    "recipe_cte_sql": check_recipe_cte_sql,
    "recipe_sample_queries": check_recipe_sample_queries,
    "table_sample_queries": check_table_sample_queries,
    "scenario_refs": check_scenario_refs,
    "glossary_links": check_glossary_links,
}


def integrity_issues(store: KnowledgeStore) -> list[str]:
    """모든 규칙의 문제를 순서를 유지하며 중복 없이 모은다."""

    issues: list[str] = []
    for check in CHECKS.values():
        issues.extend(check(store))
    return list(dict.fromkeys(issues))
