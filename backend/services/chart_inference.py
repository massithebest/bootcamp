"""SQL/시뮬레이션 결과에서 차트 스펙을 결정론적으로 추론한다. (설계: ../../docs/chart-visualization.md)

LLM 을 거치지 않는다 — `execute_sql`/`run_simulation` 이 이미 만든
`columns`/`rows` 를 그 자리에서 그대로 보고 판단한다. 별도 tool 로 만들지
않는 이유는 설계 문서 §3 참고 (LLM 이 숫자를 tool 인자로 옮겨 적으면
transcription 오류·토큰·지연 비용이 생긴다). 현재 bar/line 만 지원한다 —
간트는 범위 밖(설계 문서 §열린 질문).
"""

from __future__ import annotations

import re
from typing import Any


#: bar/line 각각 최대로 담는 항목 수. 넘는 만큼은 `truncated`/`hiddenCount` 로 알린다.
MAX_CHART_ITEMS = 20

_DATE_COL_RE = re.compile(r"(date|일자|^work_date$|월$|month)", re.I)
_CODE_COL_RE = re.compile(r"_cd$", re.I)
_NAME_COL_RE = re.compile(r"_nm$", re.I)


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric_columns(columns: list[str], rows: list[list]) -> list[int]:
    if not rows:
        return []
    return [i for i in range(len(columns)) if all(_is_numeric(row[i]) for row in rows)]


def _drop_redundant_code_columns(
    columns: list[str], rows: list[list]
) -> tuple[list[str], list[list]]:
    """`line_cd`+`line_nm` 처럼 코드/명 쌍이 함께 오면, 사람이 읽는 `_nm` 쪽만
    남기고 `_cd`를 버린다 — 카탈로그 명명 관례(`knowledge/catalog/tables/*.yaml`)를
    이용해 "같은 개체의 두 표현"이 서로 다른 그룹으로 오인되는 것을 막는다.
    """

    drop: set[int] = set()
    for i, col in enumerate(columns):
        if not _CODE_COL_RE.search(col):
            continue
        prefix = col[: -len("_cd")]
        name_idx = next(
            (
                j
                for j, other in enumerate(columns)
                if _NAME_COL_RE.search(other) and other[: -len("_nm")] == prefix
            ),
            None,
        )
        if name_idx is not None:
            drop.add(i)

    if not drop:
        return columns, rows

    keep = [i for i in range(len(columns)) if i not in drop]
    return [columns[i] for i in keep], [[row[i] for i in keep] for row in rows]


def infer_chart(columns: list[str], rows: list[list]) -> dict[str, Any] | None:
    """`columns`/`rows` 로부터 차트 스펙을 만든다. 판단할 근거가 없으면 None."""

    if not columns or not rows:
        return None

    columns, rows = _drop_redundant_code_columns(columns, rows)

    numeric_cols = _numeric_columns(columns, rows)
    non_numeric_cols = [i for i in range(len(columns)) if i not in numeric_cols]
    date_idx = next(
        (i for i in non_numeric_cols if _DATE_COL_RE.search(columns[i])), None
    )

    if len(numeric_cols) != 1 or not non_numeric_cols:
        return None

    # {그룹, 날짜, 숫자} 형태 (예: 실적_조회의 {line, workMonth, qty}) — 날짜를
    # x축으로, 나머지 비숫자 컬럼을 그룹으로 묶어 그룹별 line 시리즈를 만든다.
    if date_idx is not None and len(non_numeric_cols) == 2:
        return _grouped_line_chart(columns, rows, date_idx, non_numeric_cols, numeric_cols[0])

    if len(non_numeric_cols) != 1:
        return None

    x_idx = non_numeric_cols[0]
    value_col = columns[numeric_cols[0]]
    chart_type = "line" if date_idx is not None else "bar"

    sorted_rows = rows
    if chart_type == "bar":
        sorted_rows = sorted(rows, key=lambda r: r[numeric_cols[0]], reverse=True)

    limited = sorted_rows[:MAX_CHART_ITEMS]
    hidden = len(sorted_rows) - len(limited)

    chart: dict[str, Any] = {
        "type": chart_type,
        "x": columns[x_idx],
        "categories": [row[x_idx] for row in limited],
        "series": [{"key": value_col, "label": value_col}],
        "data": [
            {columns[x_idx]: row[x_idx], value_col: row[numeric_cols[0]]}
            for row in limited
        ],
    }
    if hidden > 0:
        chart["truncated"] = True
        chart["hiddenCount"] = hidden
    return chart


def _grouped_line_chart(
    columns: list[str],
    rows: list[list],
    date_idx: int,
    non_numeric_cols: list[int],
    value_idx: int,
) -> dict[str, Any] | None:
    group_idx = next(i for i in non_numeric_cols if i != date_idx)
    date_col = columns[date_idx]

    categories = sorted({row[date_idx] for row in rows})
    groups = sorted({row[group_idx] for row in rows})
    if len(groups) > MAX_CHART_ITEMS:
        return None

    by_key = {(row[date_idx], row[group_idx]): row[value_idx] for row in rows}
    data = [
        {date_col: cat, **{group: by_key.get((cat, group)) for group in groups}}
        for cat in categories
    ]

    return {
        "type": "line",
        "x": date_col,
        "categories": categories,
        "series": [{"key": group, "label": str(group)} for group in groups],
        "data": data,
    }


def infer_chart_from_records(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """`run_simulation` 의 레코드(dict) 배열 결과를 `infer_chart` 로 어댑팅한다."""

    if not records:
        return None
    columns = list(records[0].keys())
    rows = [[record.get(col) for col in columns] for record in records]
    return infer_chart(columns, rows)
