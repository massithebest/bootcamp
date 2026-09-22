"""저장 결과 조회 API·`present` 검증이 공유하는 오류 계약."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


#: HTTP 상태와 안전한 code. 없음·만료·다른 scope·손상은 모두 RESULT_NOT_FOUND로
#: 통일해 다른 세션 결과의 존재 여부를 노출하지 않는다.
ERROR_STATUS: dict[str, int] = {
    "RESULT_NOT_FOUND": 404,
    "INVALID_REQUEST": 422,
    "COLUMN_NOT_FOUND": 422,
    "INVALID_COLUMN_ROLE": 422,
    "AGGREGATION_REQUIRED": 422,
    "EMPTY_RESULT": 422,
    "UNRENDERABLE_VALUES": 422,
}


@dataclass(frozen=True)
class QueryResultError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_STATUS:
            raise ValueError(f"알 수 없는 query result 오류 코드: {self.code}")
        Exception.__init__(self, self.message)

    @property
    def status_code(self) -> int:
        return ERROR_STATUS[self.code]

    def as_tool_result(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


def query_error(code: str, message: str, **details: Any) -> QueryResultError:
    return QueryResultError(code, message, details or None)
