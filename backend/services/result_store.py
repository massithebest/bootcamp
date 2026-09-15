"""조회 결과를 parquet 파일로 저장하고 ``result_id``로 참조한다."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from core.config import (
    RESULT_STORE_DIR,
    RESULT_STORE_MAX_BYTES,
    RESULT_STORE_TTL_HOURS,
)


logger = logging.getLogger(__name__)
_RESULT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_TIME_NAME_PATTERN = re.compile(
    r"(?:^date(?:_|$)|_(?:date|at)(?:_|$)|날짜|일자)", re.IGNORECASE
)


@dataclass(frozen=True)
class ResultColumn:
    name: str
    dtype: str
    role: str | None


@dataclass(frozen=True)
class ResultMeta:
    result_id: str
    row_count: int
    columns: list[ResultColumn]
    created_at: datetime
    expires_at: datetime
    source: str
    conversation_id: str | None
    path: Path
    #: 원본 조회가 저장 상한(MAX_ROWS)에서 잘렸는지. row_count는 항상 저장된
    #: 행 수이며 이 값과 무관하다 — "전체 몇 건 중 일부"를 의미하지 않는다.
    source_truncated: bool
    #: 이 결과를 조회할 수 있는 브라우저 세션 scope(불투명 토큰).
    #: None이면 접근 제어를 적용하지 않았던 이전 데이터를 뜻한다(마이그레이션 호환).
    access_scope: str | None


@dataclass(frozen=True)
class ResultPage:
    result_id: str
    offset: int
    limit: int
    rows: list[list]
    row_count: int


class ResultStore(ABC):
    @abstractmethod
    def save(
        self,
        columns: list[str],
        rows: list[list],
        *,
        source: str,
        conversation_id: str | None,
        source_truncated: bool = False,
        access_scope: str | None = None,
    ) -> ResultMeta:
        """조회 결과를 저장하고 메타데이터를 반환한다."""

    @abstractmethod
    def get_meta(self, result_id: str) -> ResultMeta | None:
        """저장 결과의 메타데이터를 반환한다."""

    @abstractmethod
    def get_page(self, result_id: str, offset: int, limit: int) -> ResultPage | None:
        """저장 결과의 일부 행을 반환한다."""

    @abstractmethod
    def load(self, result_id: str) -> pd.DataFrame:
        """저장 결과 전체를 DataFrame으로 반환한다."""

    @abstractmethod
    def delete(self, result_id: str) -> None:
        """저장 결과와 메타데이터를 삭제한다."""


def _infer_role(name: str, dtype: str) -> str | None:
    """컬럼명과 pandas dtype으로 차트용 역할을 1차 추정한다."""

    if dtype.lower().startswith("datetime64") or _TIME_NAME_PATTERN.search(name):
        return "time"
    if pd.api.types.is_numeric_dtype(dtype) and dtype.lower() != "bool":
        return "measure"
    return "category"


def _json_value(value: Any) -> Any:
    """pandas/numpy scalar를 tool payload에서 JSON 직렬화 가능한 값으로 바꾼다."""

    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    item = getattr(value, "item", None)
    scalar = item() if callable(item) else value
    if scalar is None:
        return None
    if pd.api.types.is_scalar(scalar) and pd.isna(scalar):
        return None
    return scalar


def dataframe_rows(frame: pd.DataFrame) -> list[list]:
    """DataFrame 행을 JSON 직렬화 가능한 list 형태로 바꾼다."""

    return [[_json_value(value) for value in row] for row in frame.itertuples(index=False)]


def summarize_dataframe(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """숫자 컬럼별 기초 통계를 반환한다."""

    summary: dict[str, dict[str, Any]] = {}
    for name in frame.select_dtypes(include="number").columns:
        series = frame[name]
        summary[str(name)] = {
            "min": _json_value(series.min()),
            "max": _json_value(series.max()),
            "mean": _json_value(series.mean()),
            "null_count": int(series.isna().sum()),
        }
    return summary


class LocalParquetResultStore(ResultStore):
    """로컬 디렉터리에 parquet와 JSON sidecar를 저장한다."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _parquet_path(self, result_id: str) -> Path:
        return self.directory / f"{result_id}.parquet"

    def _meta_path(self, result_id: str) -> Path:
        return self.directory / f"{result_id}.meta.json"

    def save(
        self,
        columns: list[str],
        rows: list[list],
        *,
        source: str,
        conversation_id: str | None,
        source_truncated: bool = False,
        access_scope: str | None = None,
    ) -> ResultMeta:
        result_id = uuid4().hex
        self.directory.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(rows, columns=columns)
        path = self._parquet_path(result_id)
        frame.to_parquet(path, engine="pyarrow", index=False)

        created_at = datetime.now(timezone.utc)
        meta = ResultMeta(
            result_id=result_id,
            row_count=len(frame),
            columns=[
                ResultColumn(
                    name=str(name),
                    dtype=str(frame[name].dtype),
                    role=_infer_role(str(name), str(frame[name].dtype)),
                )
                for name in frame.columns
            ],
            created_at=created_at,
            expires_at=created_at + timedelta(hours=RESULT_STORE_TTL_HOURS),
            source=source,
            conversation_id=conversation_id,
            path=path,
            source_truncated=source_truncated,
            access_scope=access_scope,
        )
        payload = asdict(meta)
        payload["created_at"] = meta.created_at.isoformat()
        payload["expires_at"] = meta.expires_at.isoformat()
        payload["path"] = str(meta.path)
        self._meta_path(result_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta

    def get_meta(self, result_id: str) -> ResultMeta | None:
        if not _RESULT_ID_PATTERN.fullmatch(result_id):
            return None
        path = self._meta_path(result_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ResultMeta(
            result_id=payload["result_id"],
            row_count=payload["row_count"],
            columns=[ResultColumn(**column) for column in payload["columns"]],
            created_at=datetime.fromisoformat(payload["created_at"]),
            expires_at=datetime.fromisoformat(payload["expires_at"]),
            source=payload["source"],
            conversation_id=payload.get("conversation_id"),
            path=Path(payload["path"]),
            source_truncated=payload.get("source_truncated", False),
            access_scope=payload.get("access_scope"),
        )

    def get_page(self, result_id: str, offset: int, limit: int) -> ResultPage | None:
        meta = self.get_meta(result_id)
        if meta is None:
            return None
        frame = pd.read_parquet(meta.path, engine="pyarrow")
        rows = dataframe_rows(frame.iloc[offset : offset + limit])
        return ResultPage(
            result_id=result_id,
            offset=offset,
            limit=limit,
            rows=rows,
            row_count=meta.row_count,
        )

    def load(self, result_id: str) -> pd.DataFrame:
        return pd.read_parquet(self._parquet_path(result_id), engine="pyarrow")

    def delete(self, result_id: str) -> None:
        if not _RESULT_ID_PATTERN.fullmatch(result_id):
            return
        self._parquet_path(result_id).unlink(missing_ok=True)
        self._meta_path(result_id).unlink(missing_ok=True)


_store: ResultStore = LocalParquetResultStore(RESULT_STORE_DIR)


def get_result_store() -> ResultStore:
    return _store


def cleanup_expired() -> int:
    """만료 결과와 디스크 상한을 넘긴 오래된 결과를 삭제한다."""

    if not isinstance(_store, LocalParquetResultStore) or not _store.directory.exists():
        return 0

    deleted = 0
    now = datetime.now(timezone.utc)
    active: list[ResultMeta] = []
    for meta_path in _store.directory.glob("*.meta.json"):
        result_id = meta_path.name.removesuffix(".meta.json")
        try:
            meta = _store.get_meta(result_id)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            logger.warning("결과 메타데이터를 읽지 못했습니다: %s", meta_path)
            continue
        if meta is None:
            continue
        if meta.expires_at < now:
            _store.delete(meta.result_id)
            deleted += 1
        else:
            active.append(meta)

    total_bytes = sum(
        path.stat().st_size for path in _store.directory.iterdir() if path.is_file()
    )
    for meta in sorted(active, key=lambda item: (item.created_at, item.result_id)):
        if total_bytes <= RESULT_STORE_MAX_BYTES:
            break
        pair_size = sum(
            path.stat().st_size
            for path in (
                _store._parquet_path(meta.result_id),
                _store._meta_path(meta.result_id),
            )
            if path.exists()
        )
        logger.warning(
            "결과 저장소 상한 초과로 오래된 결과를 삭제합니다: result_id=%s",
            meta.result_id,
        )
        _store.delete(meta.result_id)
        total_bytes -= pair_size
        deleted += 1

    return deleted
