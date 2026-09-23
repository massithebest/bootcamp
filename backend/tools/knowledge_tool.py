"""도메인 지식 조회 tool. (설계 §4)

에이전트가 카탈로그·KPI 에 접근하는 유일한 경로다. 파일 도구(`Read`/`Glob`)를
열지 않는 대신 이 tool 을 통하게 해서, 어떤 지식을 참조했는지가 전부
`tool_call` / `tool_result` 이벤트로 프론트에 관측되게 한다.

결과의 `kind` 는 `"catalog"` 다 — `"knowledge"` 는 프론트가 이미 RAG
(`search_documents`) 결과 렌더링에 쓰고 있어 충돌한다.
"""

from services.knowledge.catalog import get_store


def _catalog(catalog_type: str, data, verified: bool | None = None) -> dict:
    payload = {
        "status": "ok",
        "kind": "catalog",
        "catalog_type": catalog_type,
        "data": data,
    }
    if verified is not None:
        payload["verified"] = verified
    return payload


async def list_tables(keyword: str | None = None, tag: str | None = None) -> dict:
    """List catalog tables, optionally filtered by keyword or tag.

    Returns a summary only (table / description / grain / tags / verified).
    Call `describe_table` for columns, joins, code values and caveats.
    """

    return _catalog("table_list", get_store().list_tables(keyword, tag))


async def describe_table(table: str) -> dict:
    """Describe one table: columns, grain, joins, query/aggregation rules and visualization hints.

    Always call this before writing SQL against a table.
    """

    described = get_store().describe_table(table)
    if described.get("status") == "error":
        return described

    return _catalog("table", described, verified=described["verified"])


async def list_kpis(keyword: str | None = None) -> dict:
    """List KPI definitions, optionally filtered by keyword (name / alias)."""

    return _catalog("kpi_list", get_store().list_kpis(keyword))


async def get_kpi(kpi_id: str) -> dict:
    """Get one KPI: definition, formula, sources, baseline, shortfall rule,
    aggregation rules, recipe references, SQL template and diagnostics.
    """

    kpi = get_store().get_kpi(kpi_id)
    if kpi.get("status") == "error":
        return kpi

    return _catalog("kpi", kpi, verified=kpi["verified"])


async def list_recipes(keyword: str | None = None) -> dict:
    """List reusable CTE recipes, optionally filtered by keyword.

    Returns a summary only. Call `get_recipe` for the CTE SQL body
    and aggregation guide. Keywords also match the recipe's intended uses.
    """

    return _catalog("recipe_list", get_store().list_recipes(keyword))


async def get_recipe(recipe_id: str) -> dict:
    """Get one recipe: intended uses, output grain/columns, query/aggregation rules,
    visualization hints, CTE SQL, source tables and sample queries.

    Copy `cte_sql` into your own `WITH <cte_name> AS (...)` clause when
    writing `execute_sql` — this is not auto-substituted.
    """

    recipe = get_store().get_recipe(recipe_id)
    if recipe.get("status") == "error":
        return recipe

    return _catalog("recipe", recipe, verified=recipe["verified"])
