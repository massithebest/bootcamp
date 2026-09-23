"""로컬 parquet Result Store 계약과 정리 정책 검증."""

from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pytest

from services.results import store as result_store
from services.results.store import LocalParquetResultStore, _infer_role


def _save(store: LocalParquetResultStore, rows: list[list] | None = None):
    return store.save(
        ["line_cd", "qty"],
        rows or [["A", 10], ["B", 20]],
        source="execute_sql",
        conversation_id=None,
    )


def test_save_and_get_meta_round_trip(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)
    saved = store.save(
        ["line_cd", "qty"],
        [["A", 10]],
        source="execute_sql",
        conversation_id=None,
        source_truncated=True,
        access_scope="scope-a",
    )

    loaded = store.get_meta(saved.result_id)

    assert loaded is not None
    assert loaded.row_count == saved.row_count
    assert loaded.columns == saved.columns
    assert loaded.row_count == 1
    assert loaded.source_truncated is True
    assert loaded.access_scope == "scope-a"


def test_get_page_returns_requested_slice(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)
    saved = _save(store)

    page = store.get_page(saved.result_id, offset=1, limit=1)

    assert page is not None
    assert page.rows == [["B", 20]]
    assert page.row_count == 2


def test_sidecar_path_is_ignored_and_derived_from_result_id(tmp_path) -> None:
    store_dir = tmp_path / "store"
    store = LocalParquetResultStore(store_dir)
    saved = _save(store)
    outside_path = tmp_path / "outside.parquet"
    pd.DataFrame([["outside", 999]], columns=["line_cd", "qty"]).to_parquet(
        outside_path, engine="pyarrow", index=False
    )
    sidecar = store_dir / f"{saved.result_id}.meta.json"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["path"] = str(outside_path)
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.get_meta(saved.result_id)
    page = store.get_page(saved.result_id, offset=0, limit=2)

    assert loaded is not None and loaded.path == store_dir / f"{saved.result_id}.parquet"
    assert page is not None and page.rows == [["A", 10], ["B", 20]]


def test_get_meta_rejects_sidecar_with_mismatched_result_id(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)
    saved = _save(store)
    sidecar = tmp_path / f"{saved.result_id}.meta.json"
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["result_id"] = "f" * 32
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    assert store.get_meta(saved.result_id) is None
    assert store.get_page(saved.result_id, offset=0, limit=10) is None


def test_load_rejects_noncanonical_result_id(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)

    with pytest.raises(ValueError, match="Invalid result_id"):
        store.load("../outside")


def test_load_returns_saved_dataframe(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)
    saved = _save(store)

    actual = store.load(saved.result_id)
    expected = pd.DataFrame([["A", 10], ["B", 20]], columns=["line_cd", "qty"])

    pd.testing.assert_frame_equal(actual, expected)


def test_delete_removes_result_and_is_idempotent(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)
    saved = _save(store)

    store.delete(saved.result_id)
    store.delete(saved.result_id)

    assert store.get_meta(saved.result_id) is None


def test_unknown_result_returns_none(tmp_path) -> None:
    store = LocalParquetResultStore(tmp_path)

    assert store.get_meta("missing") is None
    assert store.get_page("missing", offset=0, limit=10) is None


def test_infer_role() -> None:
    assert _infer_role("qty", "int64") == "measure"
    assert _infer_role("line_cd", "object") == "category"
    assert _infer_role("work_date", "object") == "time"
    assert _infer_role("created_at_local", "object") == "time"


def test_cleanup_expired_removes_only_expired(tmp_path, monkeypatch) -> None:
    store = LocalParquetResultStore(tmp_path)
    monkeypatch.setattr(result_store, "_store", store)
    expired = _save(store, [["A", 1]])
    active = _save(store, [["B", 2]])

    meta_path = tmp_path / f"{expired.result_id}.meta.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    meta_path.write_text(json.dumps(payload), encoding="utf-8")

    assert result_store.cleanup_expired() == 1
    assert store.get_meta(expired.result_id) is None
    assert store.get_meta(active.result_id) is not None


def test_cleanup_respects_max_bytes(tmp_path, monkeypatch) -> None:
    store = LocalParquetResultStore(tmp_path)
    monkeypatch.setattr(result_store, "_store", store)
    oldest = _save(store, [["A", 1]])
    newest = _save(store, [["B", 2]])
    total_bytes = sum(path.stat().st_size for path in tmp_path.iterdir())
    monkeypatch.setattr(result_store, "RESULT_STORE_MAX_BYTES", total_bytes - 1)

    assert result_store.cleanup_expired() == 1
    assert store.get_meta(oldest.result_id) is None
    assert store.get_meta(newest.result_id) is not None
