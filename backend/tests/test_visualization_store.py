"""시각화 메타데이터 영속 저장소 계약."""

from datetime import datetime, timedelta, timezone
import json

from services.result_store import LocalParquetResultStore
from services.visualization_models import (
    NormalizedSeries,
    NormalizedVisualizationSpec,
    VisualizationWarning,
)
from services.visualization_store import LocalVisualizationStore


def _spec() -> NormalizedVisualizationSpec:
    return NormalizedVisualizationSpec(
        kind="line",
        x="work_month",
        y=("actual",),
        group_by=None,
        series=(NormalizedSeries(key="series_0", label="actual", y="actual"),),
        x_label="work_month",
        y_label="actual",
    )


def _save(store: LocalVisualizationStore, result_id: str = "a" * 32):
    return store.save(
        result_id=result_id,
        spec=_spec(),
        warnings=(VisualizationWarning("SOURCE_TRUNCATED", "잘림"),),
        access_scope="scope-a",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def test_round_trip_survives_reinstantiation(tmp_path) -> None:
    saved = _save(LocalVisualizationStore(tmp_path))

    loaded = LocalVisualizationStore(tmp_path).get(saved.visualization_id)

    assert loaded == saved


def test_new_representation_gets_new_immutable_id(tmp_path) -> None:
    store = LocalVisualizationStore(tmp_path)
    first = _save(store)
    second = _save(store)

    assert first.visualization_id != second.visualization_id
    assert store.get(first.visualization_id) == first


def test_sidecar_contains_no_chart_data_or_html(tmp_path) -> None:
    store = LocalVisualizationStore(tmp_path)
    saved = _save(store)
    payload = json.loads(
        (tmp_path / f"{saved.visualization_id}.meta.json").read_text(encoding="utf-8")
    )

    assert "data" not in json.dumps(payload)
    assert "html" not in json.dumps(payload).lower()


def test_delete_for_result_removes_all_linked_specs(tmp_path) -> None:
    store = LocalVisualizationStore(tmp_path)
    first = _save(store, "a" * 32)
    second = _save(store, "a" * 32)
    other = _save(store, "b" * 32)

    assert store.delete_for_result("a" * 32) == 2
    assert store.get(first.visualization_id) is None
    assert store.get(second.visualization_id) is None
    assert store.get(other.visualization_id) is not None


def test_cleanup_removes_expired_orphan_and_corrupt_sidecars(tmp_path) -> None:
    results = LocalParquetResultStore(tmp_path / "results")
    active_result = results.save(
        ["month", "qty"],
        [["2026-09", 1]],
        source="execute_sql",
        conversation_id=None,
        access_scope="scope-a",
    )
    store = LocalVisualizationStore(tmp_path / "visualizations")
    active = _save(store, active_result.result_id)
    orphan = _save(store, "f" * 32)
    corrupt = store.directory / f"{'e' * 32}.meta.json"
    corrupt.write_text("{", encoding="utf-8")

    assert store.cleanup_expired(results) == 2
    assert store.get(active.visualization_id) is not None
    assert store.get(orphan.visualization_id) is None
    assert not corrupt.exists()


def test_invalid_id_and_corrupt_sidecar_are_safe(tmp_path) -> None:
    store = LocalVisualizationStore(tmp_path)
    tmp_path.mkdir(exist_ok=True)
    path = tmp_path / f"{'a' * 32}.meta.json"
    path.write_text("not json", encoding="utf-8")

    assert store.get("../escape") is None
    assert store.get("a" * 32) is None
