"""SMT2020 SQLite 연결 helper. mock SQL / 시뮬레이션 서비스가 공유한다.

두 경로가 한 데이터를 봐야 한다 (설계 §6-1) — SQL 결과와 시뮬레이션 결과가
모순되면 에이전트가 잘못된 가설을 채택한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.config import SMT2020_DB_PATH
from services.service_logging import logged_service_operation


MISSING_DB_MESSAGE = (
    "SMT2020 DB가 없습니다. python -m scripts.build_smt2020_db 를 실행하세요."
)


class Smt2020DbMissingError(FileNotFoundError):
    """SMT2020 DB가 아직 생성되지 않았다."""

    def __init__(self) -> None:
        super().__init__(MISSING_DB_MESSAGE)


@logged_service_operation
def connect() -> sqlite3.Connection:
    """읽기 전용 연결. `SMT2020_DB_PATH`는 호출 시점에 읽는다."""

    from core import config

    db_path = Path(getattr(config, "SMT2020_DB_PATH", SMT2020_DB_PATH))
    if not db_path.exists():
        raise Smt2020DbMissingError()

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
