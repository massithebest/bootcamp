"""도메인 지식 저장소 로더.

`knowledge/` 아래의 YAML(카탈로그·KPI·시뮬레이션·용어집·시나리오)을 읽어
pydantic 으로 검증하고, tool/서비스/API 가 함께 쓰는 조회 인터페이스를 제공한다.

설계: docs/domain-knowledge.md §3
- YAML 이 카탈로그·KPI·시뮬레이션 정의의 source of truth 다.
- 에이전트는 tools/knowledge_tool.py 를 통해서만 이 데이터에 접근한다.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ValidationError, model_validator

from core.config import KNOWLEDGE_DIR


# ---- 모델 ----


class KnowledgeMeta(BaseModel):
    """모든 지식 항목이 공통으로 갖는 출처/신뢰도 메타데이터."""

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


class KnowledgeTable(KnowledgeMeta):
    table: str
    description: str
    grain: list[str]
    time_column: str | None = None
    tags: list[str] = []
    columns: list[Column]
    joins: list[Join] = []
    caveats: list[str] = []
    sample_sql: str = ""


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
    follows: list[str] = []


class GlossaryEntry(KnowledgeMeta):
    term: str
    definition: str
    aliases: list[str] = []
    related_kpis: list[str] = []
    related_tables: list[str] = []


class Scenario(BaseModel):
    """합성 시드 DB 에 심을 이상치 정의. 시드 스크립트와 테스트가 공유한다."""

    name: str
    description: str
    period: tuple[date, date]
    line_cd: str
    product_id: str
    drop_ratio: float
    cause: Literal["material_shortage", "plan_change", "production_shortfall"]
    unchanged: list[str] = []
    expected_diagnosis: str


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
        scenarios: list[Scenario],
    ) -> None:
        self.tables = {table.table: table for table in tables}
        self.kpis = {kpi.kpi_id: kpi for kpi in kpis}
        self.simulations = {sim.type: sim for sim in simulations}
        self.glossary = glossary
        self.scenarios = {scenario.name: scenario for scenario in scenarios}

    # -- 로드 --

    @classmethod
    def load(cls, root: Path | str) -> "KnowledgeStore":
        """`root` 아래 YAML 을 전부 읽어 검증한다. 없는 디렉터리는 빈 목록."""

        root = Path(root)

        tables = [
            _parse(KnowledgeTable, _read_yaml(path), path)
            for path in sorted(root.glob("catalog/tables/*.yaml"))
        ]
        kpis = [
            _parse(KnowledgeKpi, _read_yaml(path), path)
            for path in sorted(root.glob("kpi/*.yaml"))
        ]
        simulations = [
            _parse(KnowledgeSimulation, _read_yaml(path), path)
            for path in sorted(root.glob("simulations/*.yaml"))
        ]
        scenarios = [
            _parse(Scenario, _read_yaml(path), path)
            for path in sorted(root.glob("scenarios/*.yaml"))
        ]

        glossary_path = root / "glossary.yaml"
        glossary: list[GlossaryEntry] = []
        if glossary_path.exists():
            raw = _read_yaml(glossary_path) or []
            if not isinstance(raw, list):
                raise ValueError(f"{glossary_path.name}: 최상위가 리스트여야 합니다.")
            glossary = [_parse(GlossaryEntry, item, glossary_path) for item in raw]

        return cls(tables, kpis, simulations, glossary, scenarios)

    # -- 조회 (tool / API 공용) --

    def list_tables(
        self, keyword: str | None = None, tag: str | None = None
    ) -> list[dict]:
        rows = []
        for table in self.tables.values():
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

    def describe_table(self, table: str) -> dict:
        found = self.tables.get(table) or self._find_ci(self.tables, table)
        if found is None:
            return self._not_found("테이블", table, "list_tables")
        return {**found.model_dump(mode="json"), "verified": self._verified(found)}

    def list_kpis(self, keyword: str | None = None) -> list[dict]:
        rows = []
        for kpi in self.kpis.values():
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

    def get_kpi(self, kpi_id: str) -> dict:
        found = self.kpis.get(kpi_id) or self._find_ci(self.kpis, kpi_id)
        if found is None:
            return self._not_found("KPI", kpi_id, "list_kpis")
        return {**found.model_dump(mode="json"), "verified": self._verified(found)}

    def list_simulations(self) -> list[dict]:
        return [self._simulation_dict(sim) for sim in self.simulations.values()]

    def get_simulation(self, simulation_type: str) -> dict:
        found = self.simulations.get(simulation_type)
        if found is None:
            return self._not_found("시뮬레이션", simulation_type, "list_simulation")
        return self._simulation_dict(found)

    def list_glossary(self) -> list[dict]:
        return [
            {**entry.model_dump(mode="json"), "verified": self._verified(entry)}
            for entry in self.glossary
        ]

    def list_scenarios(self) -> list[Scenario]:
        return list(self.scenarios.values())

    def table_names(self) -> set[str]:
        """execute_sql 가드레일이 쓰는 허용 테이블 목록."""

        return set(self.tables)

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

    def _simulation_dict(self, sim: KnowledgeSimulation) -> dict:
        return {**sim.model_dump(mode="json"), "verified": self._verified(sim)}

    @staticmethod
    def _not_found(label: str, key: str, hint_tool: str) -> dict:
        return {
            "status": "error",
            "message": f"알 수 없는 {label}입니다: {key}. {hint_tool} 로 확인하세요.",
        }


_store: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    """`KNOWLEDGE_DIR` 에서 로드한 저장소를 캐시해 돌려준다."""

    global _store
    if _store is None:
        _store = KnowledgeStore.load(KNOWLEDGE_DIR)
    return _store


def reset_store() -> None:
    """테스트에서 `KNOWLEDGE_DIR` 를 바꾼 뒤 캐시를 비우는 용도."""

    global _store
    _store = None
