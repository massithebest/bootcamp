"""저장된 조회 결과를 에이전트 Tool payload로 노출한다."""

from services.result_store import get_result_store, summarize_dataframe


def _not_found(result_id: str) -> dict:
    return {
        "status": "error",
        "message": f"result_id를 찾을 수 없습니다(만료되었을 수 있음): {result_id}",
    }


async def get_result_summary(result_id: str) -> dict:
    store = get_result_store()
    meta = store.get_meta(result_id)
    if meta is None:
        return _not_found(result_id)

    frame = store.load(result_id)
    return {
        "status": "ok",
        "result_id": result_id,
        "row_count": meta.row_count,
        "columns": [
            {"name": column.name, "dtype": column.dtype, "role": column.role}
            for column in meta.columns
        ],
        "summary": summarize_dataframe(frame),
    }


async def get_result_page(result_id: str, offset: int, limit: int) -> dict:
    page = get_result_store().get_page(result_id, offset, limit)
    if page is None:
        return _not_found(result_id)

    return {
        "status": "ok",
        "result_id": result_id,
        "offset": page.offset,
        "limit": page.limit,
        "row_count": page.row_count,
        "rows": page.rows,
    }
