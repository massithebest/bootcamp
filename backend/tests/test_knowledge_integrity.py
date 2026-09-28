"""실행 중인 `KNOWLEDGE_DIR` 디렉터리의 정합성 검사. (설계 §6 "정합성 검사")

지식은 개발 중 계속 늘어난다. 여기서 막는 것은 서로를 가리키는 참조가
끊기는 경우 — 카탈로그에 없는 테이블을 KPI 가 원천으로 적거나,
diagnostics 가 존재하지 않는 시뮬레이션을 가리키는 상황이다.
규칙 본문은 변경 요청 승인 게이트와 공유하는 `services/knowledge/integrity.py`에 있다.
"""

import pytest

from core.config import KNOWLEDGE_DIR
from services.knowledge.integrity import CHECKS
from services.knowledge.catalog import KnowledgeStore


@pytest.fixture(scope="module")
def store() -> KnowledgeStore:
    return KnowledgeStore.load(KNOWLEDGE_DIR)


def test_all_yaml_loads(store: KnowledgeStore) -> None:
    assert store.tables, "카탈로그 테이블이 하나도 로드되지 않았다"


def test_sample_queries_keep_question_and_sql_only(store: KnowledgeStore) -> None:
    samples = [s for t in store.tables.values() for s in t.sample_queries]
    samples += [s for r in store.recipes.values() for s in r.sample_queries]
    assert all(set(sample.model_dump()) == {"question", "sql"} for sample in samples)


@pytest.mark.parametrize("name", list(CHECKS))
def test_integrity_check(store: KnowledgeStore, name: str) -> None:
    assert CHECKS[name](store) == []
