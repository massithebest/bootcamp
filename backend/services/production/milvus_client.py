"""Milvus 클라이언트·임베딩 함수 스텁.

폐쇄망 이식 대상이다. 반입되는 `milvus_client.py`의 `get_embedding_function`,
`get_milvus_client`(`docs/CLOSED_NETWORK_SETUP.md` §2-1)를 여기에 병합한다.
lazy_builder 패턴을 유지해, 이 모듈이 import되는 시점(`services/production/rag_service.py`)에는
아직 실제 연결을 만들지 않는다 — 호출 시점에만 연결한다.
"""

from core.config import (
    IFLOW_EMBEDDING_ENDPOINT,
    IFLOW_EMBEDDING_KEY,
    MILVUS_COLLECTION,
    MILVUS_HOST,
    MILVUS_PORT,
    require_production_env,
)


def get_embedding_function():
    """iFlow 임베딩 함수를 지연 생성해 반환한다."""

    require_production_env("IFLOW_EMBEDDING_ENDPOINT", IFLOW_EMBEDDING_ENDPOINT)
    require_production_env("IFLOW_EMBEDDING_KEY", IFLOW_EMBEDDING_KEY)

    # TODO: 폐쇄망 pntfp의 milvus_client.py 임베딩 함수 이식
    raise NotImplementedError(
        "get_embedding_function은 폐쇄망 이식 대상입니다. "
        "docs/CLOSED_NETWORK_SETUP.md §2-4 참고."
    )


def get_milvus_client():
    """Milvus 클라이언트를 지연 생성해 반환한다(lazy_builder 유지)."""

    require_production_env("MILVUS_HOST", MILVUS_HOST)
    require_production_env("MILVUS_PORT", MILVUS_PORT)
    require_production_env("MILVUS_COLLECTION", MILVUS_COLLECTION)

    # TODO: 폐쇄망 pntfp의 milvus_client.py 연결 로직 이식
    raise NotImplementedError(
        "get_milvus_client는 폐쇄망 이식 대상입니다. "
        "docs/CLOSED_NETWORK_SETUP.md §2-4 참고."
    )
