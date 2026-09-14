"""시드 DB 가 시나리오대로 이상치를 만들었는지 확인한다. (설계 §6-1)

여기서 검증하는 것은 "찾아낼 원인이 실제로 데이터에 있는가"다. E2E 에서
에이전트가 원인을 못 찾았을 때, 데이터 문제인지 지식 문제인지 가르는 기준이 된다.
"""

import sqlite3
from pathlib import Path

import pytest

from core.config import KNOWLEDGE_DIR
from scripts.seed_sample_db import main as seed_main
from services.knowledge_service import KnowledgeStore, Scenario


SHORTFALL_THRESHOLD = 0.9


@pytest.fixture(scope="module")
def store() -> KnowledgeStore:
    return KnowledgeStore.load(KNOWLEDGE_DIR)


@pytest.fixture(scope="module")
def db(tmp_path_factory) -> Path:
    return seed_main(tmp_path_factory.mktemp("seed") / "sample.sqlite")


def _achievement_rate(db: Path, store: KnowledgeStore, line_cd: str, start: str, end: str) -> float:
    """KPI sql_template 을 기간에 맞춰 실행하고 전체 달성률을 낸다."""

    sql = store.kpis["fgs_inbound"].sql_template.replace(":from", "?").replace(":to", "?")
    with sqlite3.connect(db) as conn:
        rows = conn.execute(sql, (start, end)).fetchall()

    actual = sum(row[2] for row in rows if row[1] == line_cd)
    plan = sum(row[3] for row in rows if row[1] == line_cd)
    assert plan > 0, f"{line_cd} 라인 {start}~{end} 계획이 없다"
    return actual / plan


def _scenarios(store: KnowledgeStore) -> list[Scenario]:
    scenarios = store.list_scenarios()
    assert scenarios, "시나리오가 하나도 없다"
    return scenarios


def test_scenario_period_is_shortfall(db: Path, store: KnowledgeStore) -> None:
    for scenario in _scenarios(store):
        start, end = (day.isoformat() for day in scenario.period)
        rate = _achievement_rate(db, store, scenario.line_cd, start, end)

        assert rate < SHORTFALL_THRESHOLD, (
            f"{scenario.name}: 기간 내 달성률이 부진 기준 미만이어야 한다 (실제 {rate:.3f})"
        )


def test_outside_scenario_period_is_normal(db: Path, store: KnowledgeStore) -> None:
    for scenario in _scenarios(store):
        rate = _achievement_rate(db, store, scenario.line_cd, "2026-07-01", "2026-07-31")

        assert rate >= SHORTFALL_THRESHOLD, (
            f"{scenario.name}: 시나리오 기간 밖(7월)은 정상이어야 한다 (실제 {rate:.3f})"
        )


def test_material_shortage_rows_exist_in_period(db: Path, store: KnowledgeStore) -> None:
    with sqlite3.connect(db) as conn:
        for scenario in _scenarios(store):
            if scenario.cause != "material_shortage":
                continue
            start, end = (day.isoformat() for day in scenario.period)
            count, = conn.execute(
                """
                SELECT COUNT(*) FROM MATERIAL_SHORTAGE
                 WHERE work_date BETWEEN ? AND ? AND product_id = ?
                """,
                (start, end, scenario.product_id),
            ).fetchone()

            assert count > 0, f"{scenario.name}: 결품 행이 심어지지 않았다"


def test_unchanged_tables_keep_no_trace(db: Path, store: KnowledgeStore) -> None:
    """기각돼야 할 가설(계획 변경)의 흔적이 남으면 안 된다."""

    with sqlite3.connect(db) as conn:
        changed = [row[0] for row in conn.execute("SELECT changed FROM MP_VERSION")]

    assert set(changed) == {0}, "MP_VERSION.changed 가 전부 0 이어야 한다"


def test_seed_is_deterministic(tmp_path: Path, store: KnowledgeStore) -> None:
    def sample(path: Path) -> list[tuple]:
        with sqlite3.connect(seed_main(path)) as conn:
            return conn.execute(
                """
                SELECT work_date, line_cd, product_id, inbound_qty, status_cd
                  FROM FGS_INBOUND_RESULT ORDER BY 1, 2, 3 LIMIT 20
                """
            ).fetchall()

    assert sample(tmp_path / "a.sqlite") == sample(tmp_path / "b.sqlite")
