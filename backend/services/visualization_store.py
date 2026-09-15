"""검증된 시각화 명세를 로컬 JSON sidecar로 영속 저장한다."""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.config import VISUALIZATION_STORE_DIR
from services.result_store import ResultStore, get_result_store
from services.visualization_models import (
    NormalizedSeries,
    NormalizedVisualizationSpec,
    VisualizationMeta,
    VisualizationWarning,
)


logger = logging.getLogger(__name__)
SCHEMA_VERSION = 1
_VISUALIZATION_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class VisualizationStore(ABC):
    @abstractmethod
    def save(
        self,
        *,
        result_id: str,
        spec: NormalizedVisualizationSpec,
        warnings: tuple[VisualizationWarning, ...],
        access_scope: str,
        expires_at: datetime,
    ) -> VisualizationMeta:
        """새 불변 시각화 명세를 저장한다."""

    @abstractmethod
    def get(self, visualization_id: str) -> VisualizationMeta | None:
        """명세를 읽는다. 잘못된 ID나 손상된 파일은 None을 반환한다."""

    @abstractmethod
    def delete(self, visualization_id: str) -> None:
        """명세 하나를 삭제한다."""

    @abstractmethod
    def delete_for_result(self, result_id: str) -> int:
        """원본 결과에 연결된 모든 명세를 삭제한다."""

    @abstractmethod
    def cleanup_expired(self, result_store: ResultStore | None = None) -> int:
        """만료되었거나 원본이 사라진 명세를 정리한다."""


def _series_payload(series: NormalizedSeries) -> dict[str, Any]:
    return {
        "key": series.key,
        "label": series.label,
        "y": series.y,
        "group_value": series.group_value,
    }


def _spec_payload(spec: NormalizedVisualizationSpec) -> dict[str, Any]:
    return {
        "kind": spec.kind,
        "x": spec.x,
        "y": list(spec.y),
        "group_by": spec.group_by,
        "series": [_series_payload(series) for series in spec.series],
        "title": spec.title,
        "x_label": spec.x_label,
        "y_label": spec.y_label,
        "unit": spec.unit,
    }


def _meta_payload(meta: VisualizationMeta) -> dict[str, Any]:
    return {
        "visualization_id": meta.visualization_id,
        "result_id": meta.result_id,
        "schema_version": meta.schema_version,
        "spec": _spec_payload(meta.spec),
        "warnings": [
            {"code": warning.code, "message": warning.message}
            for warning in meta.warnings
        ],
        "access_scope": meta.access_scope,
        "created_at": meta.created_at.isoformat(),
        "expires_at": meta.expires_at.isoformat(),
    }


def _parse_meta(payload: dict[str, Any]) -> VisualizationMeta:
    spec_payload = payload["spec"]
    spec = NormalizedVisualizationSpec(
        kind=spec_payload["kind"],
        x=spec_payload["x"],
        y=tuple(spec_payload["y"]),
        group_by=spec_payload.get("group_by"),
        series=tuple(NormalizedSeries(**series) for series in spec_payload["series"]),
        title=spec_payload.get("title"),
        x_label=spec_payload.get("x_label"),
        y_label=spec_payload.get("y_label"),
        unit=spec_payload.get("unit"),
    )
    meta = VisualizationMeta(
        visualization_id=payload["visualization_id"],
        result_id=payload["result_id"],
        schema_version=int(payload["schema_version"]),
        spec=spec,
        warnings=tuple(
            VisualizationWarning(**warning) for warning in payload.get("warnings", [])
        ),
        access_scope=payload["access_scope"],
        created_at=datetime.fromisoformat(payload["created_at"]),
        expires_at=datetime.fromisoformat(payload["expires_at"]),
    )
    if meta.schema_version != SCHEMA_VERSION:
        raise ValueError("지원하지 않는 visualization schema_version")
    return meta


class LocalVisualizationStore(VisualizationStore):
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _meta_path(self, visualization_id: str) -> Path:
        return self.directory / f"{visualization_id}.meta.json"

    def save(
        self,
        *,
        result_id: str,
        spec: NormalizedVisualizationSpec,
        warnings: tuple[VisualizationWarning, ...],
        access_scope: str,
        expires_at: datetime,
    ) -> VisualizationMeta:
        self.directory.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now(timezone.utc)
        meta = VisualizationMeta(
            visualization_id=uuid4().hex,
            result_id=result_id,
            schema_version=SCHEMA_VERSION,
            spec=spec,
            warnings=warnings,
            access_scope=access_scope,
            created_at=created_at,
            expires_at=expires_at,
        )
        destination = self._meta_path(meta.visualization_id)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(_meta_payload(meta), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return meta

    def get(self, visualization_id: str) -> VisualizationMeta | None:
        if not _VISUALIZATION_ID_PATTERN.fullmatch(visualization_id):
            return None
        path = self._meta_path(visualization_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            meta = _parse_meta(payload)
            if meta.visualization_id != visualization_id:
                return None
            return meta
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            logger.warning("시각화 메타데이터를 읽지 못했습니다: %s", path)
            return None

    def delete(self, visualization_id: str) -> None:
        if _VISUALIZATION_ID_PATTERN.fullmatch(visualization_id):
            self._meta_path(visualization_id).unlink(missing_ok=True)

    def delete_for_result(self, result_id: str) -> int:
        if not self.directory.exists():
            return 0
        deleted = 0
        for path in self.directory.glob("*.meta.json"):
            visualization_id = path.name.removesuffix(".meta.json")
            meta = self.get(visualization_id)
            if meta is not None and meta.result_id == result_id:
                self.delete(visualization_id)
                deleted += 1
        return deleted

    def cleanup_expired(self, result_store: ResultStore | None = None) -> int:
        if not self.directory.exists():
            return 0
        results = result_store or get_result_store()
        now = datetime.now(timezone.utc)
        deleted = 0
        for path in self.directory.glob("*.meta.json"):
            visualization_id = path.name.removesuffix(".meta.json")
            meta = self.get(visualization_id)
            remove = meta is None
            if meta is not None:
                try:
                    result_meta = results.get_meta(meta.result_id)
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    result_meta = None
                remove = (
                    meta.expires_at <= now
                    or result_meta is None
                    or result_meta.expires_at <= now
                )
            if remove:
                path.unlink(missing_ok=True)
                deleted += 1
        return deleted


_store: VisualizationStore = LocalVisualizationStore(VISUALIZATION_STORE_DIR)


def get_visualization_store() -> VisualizationStore:
    return _store


def cleanup_expired() -> int:
    return _store.cleanup_expired(get_result_store())
