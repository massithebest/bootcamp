"""PoC 벡터 검색: 청킹, 해싱 임베딩, 활성 버전 색인과 하이브리드 검색."""

import sqlite3

import numpy as np
import pytest

from services.knowledge.documents import DocumentStore
from services.knowledge.embedding import HashingEmbedder, chunk_text, get_embedder

FIELDS = dict(title="리드타임 정책", content="승인된 리드타임은 작업 시작부터 완료까지의 시간입니다.",
              category="정책", tags=["리드타임"], owner="담당자", source="검토 회의")


@pytest.fixture
def store(tmp_path):
    return DocumentStore(tmp_path / "knowledge.sqlite3")


def publish(store, fields=FIELDS):
    doc = store.save(fields)
    doc = store.transition(doc["id"], "review", doc["revision"], version=doc["versions"][0]["version"],
                           actor="검토자", note="업무 정의 확인")
    return store.transition(doc["id"], "activate", doc["revision"], version=doc["versions"][0]["version"])


def chunk_rows(store, document_id):
    with sqlite3.connect(store.path) as conn:
        return conn.execute("SELECT version, chunk_index, start FROM chunks WHERE document_id=? ORDER BY chunk_index",
                            (document_id,)).fetchall()


def test_chunks_keep_source_offsets_and_overlap_long_blocks() -> None:
    text = "# 제목\n## 정의\n" + "문장 하나. " * 30 + "\n\n## 특징\n" + "가" * 900
    chunks = chunk_text(text)
    assert all(text[c.start:c.start + len(c.text)] == c.text for c in chunks)
    assert all(len(c.text) <= 400 for c in chunks)
    long_parts = [c for c in chunks if c.text.startswith("가")]
    assert long_parts[1].start - long_parts[0].start == 320  # 400자 중 80자 겹침
    assert chunk_text("") == [] and chunk_text("  \n\n ") == []


def test_hashing_embedding_is_deterministic_normalized_and_spacing_tolerant() -> None:
    embedder = HashingEmbedder()
    vectors = embedder.embed(["리드타임 정의", "리드 타임", "재공 관리", ""])
    assert np.allclose(vectors, HashingEmbedder().embed(["리드타임 정의", "리드 타임", "재공 관리", ""]))
    assert np.allclose(np.linalg.norm(vectors[:3], axis=1), 1.0) and not vectors[3].any()
    assert vectors[0] @ vectors[1] > vectors[0] @ vectors[2]


def test_activation_indexes_only_the_active_version(store):
    doc = publish(store)
    assert chunk_rows(store, doc["id"]) == [(1, 0, 0)]
    doc = store.save({**FIELDS, "content": "개정된 리드타임 기준"}, doc["id"], doc["revision"])
    assert chunk_rows(store, doc["id"])[0][0] == 1  # 초안은 색인하지 않는다
    doc = store.transition(doc["id"], "review", doc["revision"], version=2, actor="검토자", note="개정 확인")
    doc = store.transition(doc["id"], "activate", doc["revision"], version=2)
    assert [row[0] for row in chunk_rows(store, doc["id"])] == [2]
    store.transition(doc["id"], "deactivate", doc["revision"])
    assert chunk_rows(store, doc["id"]) == []


def test_hybrid_search_finds_spelling_variants_but_not_unrelated_queries(store):
    publish(store)
    # "리드타임들"은 본문에 그대로 없어 키워드로는 못 찾지만 문자 n-gram 이 겹친다.
    assert [d["title"] for d in store.search("리드타임들")["documents"]] == ["리드타임 정책"]
    for query in ("인사 평가", "없는검색어"):
        assert store.search(query)["documents"] == []
    assert "score" not in store.search("리드타임들")["documents"][0]


def test_snippet_starts_at_the_most_similar_chunk(store):
    content = "## 개요\n" + "일반 안내 문장입니다. " * 30 + "\n\n## 운반\n운반 시간은 출발지와 도착지 조합별로 정의한다."
    publish(store, {**FIELDS, "title": "운영 안내", "content": content, "tags": []})
    snippet = store.search("운반 시간")["documents"][0]["snippet"]
    assert snippet.startswith("## 운반")


def test_missing_or_outdated_index_is_rebuilt_on_search(store):
    doc = publish(store)
    with sqlite3.connect(store.path) as conn:
        conn.execute("UPDATE chunks SET embedder='old-embedder'")
    assert store.search("리드타임들")["documents"]
    with sqlite3.connect(store.path) as conn:
        names = {row[0] for row in conn.execute("SELECT embedder FROM chunks WHERE document_id=?", (doc["id"],))}
    assert names == {get_embedder().name}
