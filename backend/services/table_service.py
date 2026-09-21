"""저장된 조회 결과를 standalone 표 Tool UI payload로 변환한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from services.result_store import ResultMeta, ResultStore, dataframe_rows, get_result_store
from services.service_logging import logged_service_operation


TABLE_DISPLAY_ROW_LIMIT = 100
TABLE_TITLE_MAX_LENGTH = 120


@dataclass(frozen=True)
class TableError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def as_tool_result(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


def _error(code: str, message: str, **details: Any) -> TableError:
    return TableError(code, message, details or None)


def _get_result_meta(store: ResultStore, result_id: str) -> ResultMeta:
    try:
        meta = store.get_meta(result_id)
    except Exception as exc:
        raise _error("RESULT_UNAVAILABLE", "저장된 조회 결과를 읽을 수 없습니다.") from exc
    if meta is None:
        raise _error("RESULT_NOT_FOUND", "result_id를 찾을 수 없습니다.")
    if meta.expires_at <= datetime.now(timezone.utc):
        raise _error("RESULT_EXPIRED", "조회 결과가 만료되었습니다. 새로 조회해 주세요.")
    return meta


def _check_scope(meta: ResultMeta, access_scope: str | None) -> None:
    if not access_scope or not meta.access_scope or meta.access_scope != access_scope:
        raise _error("RESULT_FORBIDDEN", "이 조회 결과에 접근할 수 없습니다.")


def _normalize_columns(columns: list[str] | None, available: list[str]) -> list[str]:
    if columns is None:
        return available
    if (
        not isinstance(columns, list)
        or not columns
        or any(not isinstance(name, str) or not name.strip() for name in columns)
    ):
        raise _error("INVALID_COLUMNS", "columns에는 하나 이상의 컬럼 이름이 필요합니다.")
    normalized = [name.strip() for name in columns]
    if len(set(normalized)) != len(normalized):
        raise _error("INVALID_COLUMNS", "columns에 같은 컬럼을 중복 지정할 수 없습니다.")
    missing = [name for name in normalized if name not in available]
    if missing:
        raise _error(
            "COLUMN_NOT_FOUND",
            "조회 결과에 없는 컬럼이 지정되었습니다.",
            columns=missing,
        )
    return normalized


@logged_service_operation
def prepare_table_payload(
    result_id: str,
    *,
    columns: list[str] | None = None,
    title: str | None = None,
    access_scope: str | None,
    result_store: ResultStore | None = None,
) -> dict[str, Any]:
    """접근 가능한 결과의 앞쪽 최대 100행을 검증된 표 payload로 만든다."""

    store = result_store or get_result_store()
    meta = _get_result_meta(store, result_id)
    _check_scope(meta, access_scope)

    normalized_title = title.strip() if isinstance(title, str) else None
    if normalized_title == "":
        normalized_title = None
    if normalized_title is not None and len(normalized_title) > TABLE_TITLE_MAX_LENGTH:
        raise _error(
            "INVALID_TITLE",
            f"표 제목은 {TABLE_TITLE_MAX_LENGTH}자 이하여야 합니다.",
        )

    available = [column.name for column in meta.columns]
    selected = _normalize_columns(columns, available)
    try:
        frame = store.load(result_id).loc[:, selected].head(TABLE_DISPLAY_ROW_LIMIT)
    except TableError:
        raise
    except Exception as exc:
        raise _error(
            "RESULT_UNAVAILABLE", "저장된 조회 결과 데이터를 읽을 수 없습니다."
        ) from exc

    rows = dataframe_rows(frame)
    return {
        "status": "ok",
        "result_id": meta.result_id,
        "title": normalized_title,
        "columns": selected,
        "rows": rows,
        "row_count": meta.row_count,
        "displayed_count": len(rows),
        "source_truncated": meta.source_truncated,
    }
