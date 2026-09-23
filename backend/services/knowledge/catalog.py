"""도메인 지식 저장소 로더.

`knowledge/` 아래의 YAML(카탈로그·KPI·시뮬레이션·용어집·시나리오·레시피)을 읽어
pydantic 으로 검증하고, tool/서비스/API 가 함께 쓰는 조회 인터페이스를 제공한다.

관리 기준: backend/docs/DOMAIN-KNOWLEDGE-MANAGEMENT.md
- YAML 이 카탈로그·KPI·시뮬레이션 정의의 source of truth 다.
- 에이전트는 tools/knowledge_tool.py 를 통해서만 이 데이터에 접근한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from core.config import KNOWLEDGE_DIR
from services.service_logging import logged_service_operation


# ---- 모델 ----


class KnowledgeMeta(BaseModel):
    """모든 지식 항목이 공통으로 갖는 출처/신뢰도 메타데이터."""

    active: bool = True
    status: Literal["draft", "verified"] = "draft"
    owner: str = ""
    updated: date | None = None
    source: str = ""


class Column(BaseModel):
    name: str
    type: str
    desc: str = ""
    ref: str | None = None  # "TABLE.column"
    codes: dict[str, str] | None = None


class Join(BaseModel):
    to: str
    on: str | list[str]
    kind: str = "many-to-one"
    note: str = ""

    @model_validator(mode="before")
    @classmethod
    def _restore_on_key(cls, raw: Any) -> Any:
        """YAML 1.1 이 따옴표 없는 `on:` 을 boolean True 키로 읽는 것을 되돌린다.

        `{to: X, on: line_cd}` 처럼 쓰는 편이 카탈로그 작성자에게 자연스러우므로
        YAML 쪽에 따옴표를 강제하지 않고 여기서 흡수한다.
        """

        if isinstance(raw, dict) and True in raw and "on" not in raw:
            raw = {("on" if key is True else key): value for key, value in raw.items()}
        return raw


class SqlQueryExample(BaseModel):
    """자연어 질문과 실행 가능한 SQL 예시."""

    model_config = ConfigDict(extra="forbid")

    question: str
    sql: str


class KnowledgeTable(KnowledgeMeta):
    table: str
    description: str
    grain: list[str]
    time_column: str | None = None
    tags: list[str] = []
    columns: list[Column]
    joins: list[Join] = []
    caveats: list[str] = []
    query_rules: list[str] = []
    aggregation_rules: list[str] = []
    visualization_hints: list[str] = []
    sample_queries: list[SqlQueryExample] = []


class Diagnostic(BaseModel):
    hypothesis: str
    how: Literal["sql", "simulation"]
    ref: str


class KnowledgeKpi(KnowledgeMeta):
    kpi_id: str
    name: str
    aliases: list[str] = []
    definition: str
    formula: str
    sources: list[str]
    grain: list[str]
    baseline: str
    shortfall_rule: str
    sql_template: str
    aggregation_rules: list[str] = []
    recipe_refs: list[str] = []
    diagnostics: list[Diagnostic] = []


class SimulationParam(BaseModel):
    required: bool
    description: str
    example: str | None = None


class KnowledgeSimulation(KnowledgeMeta):
    type: str
    name: str
    aliases: list[str] = []
    when_to_use: str
    params: dict[str, SimulationParam] = {}
    output_schema: dict[str, Any] = {}
    aggregation_rules: list[str] = []
    visualization_hints: list[str] = []
    follows: list[str] = []


class GlossaryEntry(KnowledgeMeta):
    term: str
    definition: str
    aliases: list[str] = []
    related_kpis: list[str] = []
    related_tables: list[str] = []


class ScenarioStep(BaseModel):
    """검증 시나리오가 참조하는 recipe 또는 simulation 한 단계."""

    action: Literal["recipe", "simulation"]
    ref: str
    params: dict[str, str] = {}
    expectation: str


class ScenarioExpected(BaseModel):
    """고정 검증 데이터에서 바뀌면 안 되는 최소 기대값."""

    table_counts: dict[str, int] = {}
    unmatched_rows: dict[str, int] = {}


class KnowledgeScenario(KnowledgeMeta):
    """원본을 변형하지 않고 recipe/simulation을 관통 검증하는 QA 시나리오."""

    scenario_id: str
    name: str
    description: str
    dataset: str
    question: str
    steps: list[ScenarioStep]
    expected: ScenarioExpected


class RecipeOutputColumn(BaseModel):
    """CTE 출력 컬럼의 의미. role/unit 은 작성자가 명시한 집계 가이드다."""

    name: str
    role: Literal["category", "measure", "time"]
    unit: str | None = None
    desc: str = ""


class KnowledgeRecipe(KnowledgeMeta):
    """자주 쓰는 집계·조인 패턴을 담은 재사용 가능 CTE.

    에이전트는 `cte_sql` 을 `WITH <cte_name> AS (...)` 로 직접 조합해
    execute_sql 에 붙여 쓴다. 자동 치환 없음 — sql_guard 는 그대로 둔다.
    """

    recipe_id: str
    name: str
    description: str
    cte_name: str  # WITH 절에서 쓸 별칭
    cte_sql: str  # `WITH <cte_name> AS (` 와 `)` 사이에 들어갈 본문
    sources: list[str]  # cte_sql 이 읽는 실제 카탈로그 테이블
    when_to_use: list[str] = []
    output_grain: list[str] = []
    output_columns: list[RecipeOutputColumn] = []
    query_rules: list[str] = []
    aggregation_rules: list[str] = []
    visualization_hints: list[str] = []
    sample_queries: list[SqlQueryExample] = []

    @model_validator(mode="after")
    def _validate_output_contract(self) -> KnowledgeRecipe:
        if self.output_columns:
            names = [column.name for column in self.output_columns]
            if len(names) != len(set(names)):
                raise ValueError("output_columns 에 중복 컬럼명이 있습니다")
            if not set(self.output_grain) <= set(names):
                raise ValueError("output_grain 은 output_columns 에 있는 컬럼이어야 합니다")
        elif self.output_grain:
            raise ValueError("output_grain 을 지정하면 output_columns 도 필요합니다")
        return self


@dataclass(frozen=True)
class KindSpec:
    """지식 종류별 모델, 키 필드와 `knowledge/` 안의 저장 위치."""

    model: type[BaseModel]
    key_field: str
    #: 항목마다 파일 하나를 쓰는 종류의 디렉터리. glossary 는 파일 하나에 목록으로 담는다.
    directory: str | None
    attribute: str  # KnowledgeStore 의 dict 속성 이름


GLOSSARY_FILE = "glossary.yaml"

KIND_SPECS: dict[str, KindSpec] = {
    "table": KindSpec(KnowledgeTable, "table", "catalog/tables", "tables"),
    "kpi": KindSpec(KnowledgeKpi, "kpi_id", "kpi", "kpis"),
    "recipe": KindSpec(KnowledgeRecipe, "recipe_id", "recipes", "recipes"),
    "simulation": KindSpec(KnowledgeSimulation, "type", "simulations", "simulations"),
    "scenario": KindSpec(KnowledgeScenario, "scenario_id", "scenarios", "scenarios"),
    "glossary": KindSpec(GlossaryEntry, "term", None, "glossary"),
}


# ---- 로더 ----


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name}: YAML 파싱 실패 — {exc}") from exc


def _parse(model: type[BaseModel], raw: Any, path: Path) -> Any:
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"{path.name}: {model.__name__} 검증 실패 — {exc}") from exc


def _contains(needle: str, *haystacks: Any) -> bool:
    """대소문자를 무시한 부분일치. 문자열/문자열 리스트를 함께 받는다."""

    lowered = needle.lower()
    for haystack in haystacks:
        values = haystack if isinstance(haystack, list) else [haystack]
        if any(lowered in str(value).lower() for value in values):
            return True
    return False


class KnowledgeStore:
    """검증된 지식 항목의 인메모리 저장소."""

    def __init__(
        self,
        tables: list[KnowledgeTable],
        kpis: list[KnowledgeKpi],
        simulations: list[KnowledgeSimulation],
        glossary: list[GlossaryEntry],
        recipes: list[KnowledgeRecipe] | None = None,
        scenarios: list[KnowledgeScenario] | None = None,
        source_paths: dict[tuple[str, str], str] | None = None,
    ) -> None:
        #: (kind, key) -> `knowledge/` 기준 상대 경로. 파일명과 키가 다른 기존 파일을
        #: 안전하게 덮어쓰기 위한 정보이며, 직접 생성한 저장소에서는 비어 있다.
        self.source_paths = source_paths or {}
        self.tables = {table.table: table for table in tables}
        self.kpis = {kpi.kpi_id: kpi for kpi in kpis}
        self.simulations = {sim.type: sim for sim in simulations}
        self.glossary = glossary
        self.recipes = {recipe.recipe_id: recipe for recipe in (recipes or [])}
        self.scenarios = {
            scenario.scenario_id: scenario for scenario in (scenarios or [])
        }

    # -- 로드 --

    @classmethod
    @logged_service_operation
    def load(cls, root: Path | str) -> "KnowledgeStore":
        """`root` 아래 YAML 을 전부 읽어 검증한다. 없는 디렉터리는 빈 목록."""

        root = Path(root)
        source_paths: dict[tuple[str, str], str] = {}

        def read_kind(kind: str) -> list:
            spec = KIND_SPECS[kind]
            items = []
            for path in sorted(root.glob(f"{spec.directory}/*.yaml")):
                item = _parse(spec.model, _read_yaml(path), path)
                source_paths[(kind, getattr(item, spec.key_field))] = str(
                    path.relative_to(root)
                )
                items.append(item)
            return items

        tables = read_kind("table")
        kpis = read_kind("kpi")
        simulations = read_kind("simulation")
        recipes = read_kind("recipe")
        scenarios = read_kind("scenario")

        glossary_path = root / GLOSSARY_FILE
        glossary: list[GlossaryEntry] = []
        if glossary_path.exists():
            raw = _read_yaml(glossary_path) or []
            if not isinstance(raw, list):
                raise ValueError(f"{glossary_path.name}: 최상위가 리스트여야 합니다.")
            glossary = [_parse(GlossaryEntry, item, glossary_path) for item in raw]
            for entry in glossary:
                source_paths[("glossary", entry.term)] = GLOSSARY_FILE

        return cls(
            tables, kpis, simulations, glossary, recipes, scenarios, source_paths
        )

    # -- 조회 (tool / API 공용) --

    @logged_service_operation
    def list_tables(
        self, keyword: str | None = None, tag: str | None = None
    ) -> list[dict]:
        rows = []
        for table in self.tables.values():
            if not table.active:
                continue
            if keyword and not _contains(
                keyword,
                table.table,
                table.description,
                table.tags,
                [column.name for column in table.columns],
            ):
                continue
            if tag and not _contains(tag, table.tags):
                continue
            rows.append(
                {
                    "table": table.table,
                    "description": table.description,
                    "grain": table.grain,
                    "tags": table.tags,
                    "verified": self._verified(table),
                }
            )
        return rows

    @logged_service_operation
    def describe_table(self, table: str) -> dict:
        found = self.tables.get(table) or self._find_ci(self.tables, table)
        if found is None or not found.active:
            return self._not_found("테이블", table, "list_tables")
        described = {**found.model_dump(mode="json"), "verified": self._verified(found)}
        described["joins"] = [
            join for join in described["joins"] if not self._is_unavailable(join["to"], self.tables)
        ]
        return described

    @logged_service_operation
    def list_kpis(self, keyword: str | None = None) -> list[dict]:
        rows = []
        for kpi in self.kpis.values():
            if not kpi.active or self._inactive_sources(kpi):
                continue
            if keyword and not _contains(keyword, kpi.name, kpi.aliases, kpi.definition, kpi.kpi_id):
                continue
            rows.append(
                {
                    "kpi_id": kpi.kpi_id,
                    "name": kpi.name,
                    "aliases": kpi.aliases,
                    "verified": self._verified(kpi),
                }
            )
        return rows

    @logged_service_operation
    def get_kpi(self, kpi_id: str) -> dict:
        found = self.kpis.get(kpi_id) or self._find_ci(self.kpis, kpi_id)
        if found is None or not found.active:
            return self._not_found("KPI", kpi_id, "list_kpis")
        if (unavailable := self._unavailable_reason("KPI", found)) is not None:
            return unavailable
        described = {**found.model_dump(mode="json"), "verified": self._verified(found)}
        described["recipe_refs"] = [
            ref for ref in described["recipe_refs"] if not self._is_unavailable(ref, self.recipes)
        ]
        described["diagnostics"] = [
            item
            for item in described["diagnostics"]
            if not self._is_unavailable_diagnostic(item["how"], item["ref"])
        ]
        return described

    @logged_service_operation
    def list_simulations(self) -> list[dict]:
        return [
            self._simulation_dict(sim)
            for sim in self.simulations.values()
            if sim.active
        ]

    @logged_service_operation
    def get_simulation(self, simulation_type: str) -> dict:
        found = self.simulations.get(simulation_type)
        if found is None or not found.active:
            return self._not_found("시뮬레이션", simulation_type, "list_simulation")
        return self._simulation_dict(found)

    @logged_service_operation
    def list_glossary(self) -> list[dict]:
        rows = []
        for entry in self.glossary:
            if not entry.active:
                continue
            row = {**entry.model_dump(mode="json"), "verified": self._verified(entry)}
            row["related_kpis"] = [
                ref for ref in row["related_kpis"] if not self._is_unavailable(ref, self.kpis)
            ]
            row["related_tables"] = [
                ref for ref in row["related_tables"] if not self._is_unavailable(ref, self.tables)
            ]
            rows.append(row)
        return rows

    @logged_service_operation
    def list_recipes(self, keyword: str | None = None) -> list[dict]:
        rows = []
        for recipe in self.recipes.values():
            if not recipe.active or self._inactive_sources(recipe):
                continue
            if keyword and not _contains(
                keyword,
                recipe.recipe_id,
                recipe.name,
                recipe.description,
                recipe.when_to_use,
            ):
                continue
            rows.append(
                {
                    "recipe_id": recipe.recipe_id,
                    "name": recipe.name,
                    "description": recipe.description,
                    "cte_name": recipe.cte_name,
                    "verified": self._verified(recipe),
                }
            )
        return rows

    @logged_service_operation
    def get_recipe(self, recipe_id: str) -> dict:
        found = self.recipes.get(recipe_id) or self._find_ci(self.recipes, recipe_id)
        if found is None or not found.active:
            return self._not_found("레시피", recipe_id, "list_recipes")
        if (unavailable := self._unavailable_reason("레시피", found)) is not None:
            return unavailable
        return {**found.model_dump(mode="json"), "verified": self._verified(found)}

    @logged_service_operation
    def list_scenarios(self, keyword: str | None = None) -> list[dict]:
        rows = []
        for scenario in self.scenarios.values():
            if not scenario.active:
                continue
            if keyword and not _contains(
                keyword,
                scenario.scenario_id,
                scenario.name,
                scenario.description,
                scenario.dataset,
                scenario.question,
            ):
                continue
            rows.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "name": scenario.name,
                    "dataset": scenario.dataset,
                    "question": scenario.question,
                    "verified": self._verified(scenario),
                }
            )
        return rows

    @logged_service_operation
    def get_scenario(self, scenario_id: str) -> dict:
        found = self.scenarios.get(scenario_id) or self._find_ci(
            self.scenarios, scenario_id
        )
        if found is None or not found.active:
            return self._not_found("시나리오", scenario_id, "list_scenarios")
        return {**found.model_dump(mode="json"), "verified": self._verified(found)}

    @logged_service_operation
    def is_simulation_active(self, simulation_type: str) -> bool:
        """등록되어 있고 `active: true` 인 simulation 만 실행할 수 있다."""

        found = self.simulations.get(simulation_type)
        return found is not None and found.active

    @logged_service_operation
    def table_names(self) -> set[str]:
        """execute_sql 가드레일이 쓰는 허용 테이블 목록."""

        return {name for name, table in self.tables.items() if table.active}

    # -- 내부 --

    @staticmethod
    def _verified(item: KnowledgeMeta) -> bool:
        return item.status == "verified"

    @staticmethod
    def _find_ci(mapping: dict, key: str) -> Any:
        lowered = key.lower()
        for name, value in mapping.items():
            if name.lower() == lowered:
                return value
        return None

    def _inactive_sources(self, item: KnowledgeMeta) -> list[str]:
        """KPI·recipe 의 `sources` 중 등록되어 있으나 `active: false` 인 table 이름."""

        if not isinstance(item, (KnowledgeKpi, KnowledgeRecipe)):
            return []
        return [name for name in item.sources if self._is_unavailable(name, self.tables)]

    def _is_unavailable(self, key: str, mapping: dict) -> bool:
        """등록되어 있으나 Agent 가 쓸 수 없는 항목을 가리키는 참조인지 확인한다.

        `active: false` 이거나(KPI·recipe 는) 원천 table 이 비활성이면 사용할 수 없다.
        등록되지 않은 참조는 무결성 테스트의 몫이므로 여기서는 숨기지 않는다.
        """

        found = mapping.get(key)
        return found is not None and (not found.active or bool(self._inactive_sources(found)))

    def _unavailable_reason(self, label: str, item: KnowledgeMeta) -> dict | None:
        """활성이지만 원천 table 이 비활성이라 쓸 수 없으면 원인을 담은 오류를 돌려준다."""

        inactive = self._inactive_sources(item)
        if not inactive:
            return None
        return {
            "status": "error",
            "message": f"{label}의 원천 테이블이 비활성이라 사용할 수 없습니다: {', '.join(inactive)}.",
        }

    def _is_unavailable_diagnostic(self, how: str, ref: str) -> bool:
        if how == "simulation":
            return self._is_unavailable(ref, self.simulations)
        if ref.startswith("recipes/"):
            return self._is_unavailable(ref.removeprefix("recipes/"), self.recipes)
        return self._is_unavailable(ref, self.tables)

    def _simulation_dict(self, sim: KnowledgeSimulation) -> dict:
        described = {**sim.model_dump(mode="json"), "verified": self._verified(sim)}
        described["follows"] = [
            ref for ref in described["follows"] if not self._is_unavailable(ref, self.simulations)
        ]
        return described

    @staticmethod
    def _not_found(label: str, key: str, hint_tool: str) -> dict:
        return {
            "status": "error",
            "message": f"알 수 없는 {label}입니다: {key}. {hint_tool} 로 확인하세요.",
        }


_store: KnowledgeStore | None = None


@logged_service_operation
def get_store() -> KnowledgeStore:
    """`KNOWLEDGE_DIR` 에서 로드한 저장소를 캐시해 돌려준다."""

    global _store
    if _store is None:
        _store = KnowledgeStore.load(KNOWLEDGE_DIR)
    return _store


@logged_service_operation
def reset_store() -> None:
    """테스트에서 `KNOWLEDGE_DIR` 를 바꾼 뒤 캐시를 비우는 용도."""

    global _store
    _store = None
