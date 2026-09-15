"""execute_sql 가드레일. (설계 §4)

SDK 훅이 아니라 서비스 계층에 둔다 — 훅은 SDK 에 종속되지만, 이 검증은
mock / real / 테스트 어디서든 같은 규칙으로 동작해야 한다.
"""

from __future__ import annotations

import re


#: 한 번에 저장할 최대 행 수. 서비스는 MAX_ROWS + 1행으로 source_truncated를 판정한다.
MAX_ROWS = 500

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|PRAGMA)\b", re.I
)

#: `FROM`/`JOIN` 뒤의 테이블명. 앞의 `(?<![:\w.])` 는 `BETWEEN :from AND :to` 의
#: `:from` 을 FROM 절로 오인해 `AND` 를 테이블명으로 잡는 것을 막는다.
_TABLE_REF = re.compile(r"(?<![:\w.])\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)


class SqlGuardError(ValueError):
    """에이전트에게 그대로 보여줄 수 있는 거부 사유."""


def check_sql(sql: str, allowed_tables: set[str]) -> str:
    """검사를 통과하면 LIMIT 가 보장된 SQL 을 돌려준다.

    Raises:
        SqlGuardError: 조회 전용 규칙을 어겼거나 미등록 테이블을 참조할 때.
    """

    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return _with_limit(stripped)

    if ";" in stripped:
        raise SqlGuardError("한 번에 하나의 SQL 문만 실행할 수 있습니다.")

    first_token = stripped.split(None, 1)[0].upper()
    if first_token not in {"SELECT", "WITH"}:
        raise SqlGuardError(
            "조회(SELECT) 전용입니다. 데이터를 변경하는 SQL 은 실행할 수 없습니다."
        )

    forbidden = _FORBIDDEN.search(stripped)
    if forbidden:
        raise SqlGuardError(
            f"허용되지 않는 키워드가 있습니다: {forbidden.group(1).upper()}. 조회(SELECT) 전용입니다."
        )

    allowed_lower = {name.lower() for name in allowed_tables}
    # CTE 이름(`WITH x AS (...)`)은 카탈로그에 없어도 참조할 수 있다.
    allowed_lower |= {
        name.lower() for name in re.findall(r"(?:WITH|,)\s+([A-Za-z_]\w*)\s+AS\s*\(", stripped, re.I)
    }
    # 별칭이 붙은 서브쿼리(`FROM (...) t`)도 마찬가지다.

    for table in _TABLE_REF.findall(stripped):
        if table.lower() not in allowed_lower:
            raise SqlGuardError(
                f"등록되지 않은 테이블입니다: {table}. list_tables 로 확인하세요."
            )

    return _with_limit(stripped)


def _with_limit(sql: str) -> str:
    if re.search(r"\bLIMIT\b", sql, re.I):
        return sql
    return f"{sql} LIMIT {MAX_ROWS + 1}"
