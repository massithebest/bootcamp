"""차트 v2의 저장·서비스 계층 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


ChartKind = Literal["bar", "line"]


@dataclass(frozen=True)
class VisualizationRequest:
    result_id: str
    kind: str
    x: str
    y: tuple[str, ...]
    group_by: str | None = None


@dataclass(frozen=True)
class NormalizedSeries:
    key: str
    label: str
    y: str
    group_value: Any = None


@dataclass(frozen=True)
class NormalizedVisualizationSpec:
    kind: ChartKind
    x: str
    y: tuple[str, ...]
    group_by: str | None
    series: tuple[NormalizedSeries, ...]
    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class VisualizationWarning:
    code: str
    message: str


@dataclass(frozen=True)
class VisualizationMeta:
    visualization_id: str
    result_id: str
    schema_version: int
    spec: NormalizedVisualizationSpec
    warnings: tuple[VisualizationWarning, ...]
    access_scope: str
    created_at: datetime
    expires_at: datetime
