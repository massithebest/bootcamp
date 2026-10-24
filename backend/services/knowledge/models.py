"""구조화 지식 모델과 종류별 저장 위치. YAML 검증 계약의 단일 정의."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

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

    @model_validator(mode="after")
    def _validate_column_refs(self) -> KnowledgeTable:
        """grain·time_column 은 columns 에 정의된 컬럼이어야 한다(오타가 승인까지 통과하지 않게)."""

        names = {column.name for column in self.columns}
        missing = [name for name in self.grain if name not in names]
        if missing:
            raise ValueError(f"grain 은 columns 에 있는 컬럼이어야 합니다: {', '.join(missing)}")
        if self.time_column and self.time_column not in names:
            raise ValueError(f"time_column 은 columns 에 있는 컬럼이어야 합니다: {self.time_column}")
        return self


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
