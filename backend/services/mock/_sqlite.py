"""합성 시드 SQLite 연결 helper. mock SQL / 시뮬레이션 서비스가 공유한다.

두 경로가 한 데이터를 봐야 한다 (설계 §6-1) — SQL 결과와 시뮬레이션 결과가
모순되면 에이전트가 잘못된 가설을 채택한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.config import SAMPLE_DB_PATH


MISSING_DB_MESSAGE = "sample DB 가 없습니다. python -m scripts.seed_sample_db 를 실행하세요."


class SampleDbMissingError(FileNotFoundError):
    """시드 DB 가 아직 생성되지 않았다."""

    def __init__(self) -> None:
        super().__init__(MISSING_DB_MESSAGE)


def connect() -> sqlite3.Connection:
    """읽기 전용 조회용 연결. `SAMPLE_DB_PATH` 는 호출 시점에 읽는다(테스트 monkeypatch)."""

    from core import config

    db_path = Path(getattr(config, "SAMPLE_DB_PATH", SAMPLE_DB_PATH))
    if not db_path.exists():
        raise SampleDbMissingError()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
