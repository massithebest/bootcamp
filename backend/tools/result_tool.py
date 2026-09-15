"""저장된 조회 결과를 에이전트 Tool payload로 노출한다."""

from services.result_store import ResultMeta, get_result_store, summarize_dataframe


def _not_found(result_id: str) -> dict:
    return {
        "status": "error",
        "message": f"result_id를 찾을 수 없습니다(만료되었을 수 있음): {result_id}",
    }


def _forbidden_as_not_found(meta: ResultMeta, access_scope: str | None) -> bool:
    """다른 브라우저 세션의 결과인지 확인한다.

    존재 여부를 노출하지 않기 위해 접근 불가도 not-found와 같은 메시지로
    처리한다(§6.1 access scope 원칙과 동일한 비노출 정책).
    ``meta.access_scope``가 None인 결과는 scope 도입 이전 데이터라 계속
    허용한다 — 신규 저장분부터만 강제한다.
    """

    return meta.access_scope is not None and meta.access_scope != access_scope


async def get_result_summary(result_id: str, *, access_scope: str | None = None) -> dict:
    store = get_result_store()
    meta = store.get_meta(result_id)
    if meta is None or _forbidden_as_not_found(meta, access_scope):
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


async def get_result_page(
    result_id: str, offset: int, limit: int, *, access_scope: str | None = None
) -> dict:
    store = get_result_store()
    meta = store.get_meta(result_id)
    if meta is None or _forbidden_as_not_found(meta, access_scope):
        return _not_found(result_id)

    page = store.get_page(result_id, offset, limit)
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
