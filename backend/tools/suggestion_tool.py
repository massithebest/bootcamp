"""성공한 응답 뒤에 보여줄 후속질문을 검증한다.

Agent 가 `suggest_follow_ups` 로 넘긴 질문은 화면에 Tool 로 표시하지 않고,
검증을 통과한 경우에만 성공한 `done.data.suggestions` 로 전달된다.
형식이 맞지 않으면 보정하지 않고 버린다(응답 자체는 실패시키지 않는다).
"특정 제품"처럼 대상을 비워 둔 질문은 눌러도 확인 질문만 돌아오므로 그 항목만 뺀다.
"""

import re
from typing import Any

SUGGESTION_MIN = 2
SUGGESTION_MAX = 4
SUGGESTION_MAX_LENGTH = 120

_HANGUL = re.compile(r"[가-힣]")
_PLACEHOLDER_SUBJECT = re.compile(r"특정\s*\S")


def suggest_follow_ups_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": SUGGESTION_MAX_LENGTH},
                "minItems": SUGGESTION_MIN,
                "maxItems": SUGGESTION_MAX,
            },
        },
        "required": ["questions"],
        "additionalProperties": False,
    }


def normalize_suggestions(value: object) -> list[str] | None:
    """앞뒤 공백 제거·중복 제거·대상 미지정 질문 제외 후 2~4개의 한국어 질문이면 반환하고, 아니면 None."""

    if not isinstance(value, list):
        return None
    items: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if not text or len(text) > SUGGESTION_MAX_LENGTH or not _HANGUL.search(text):
            return None
        if _PLACEHOLDER_SUBJECT.search(text):
            continue
        if text not in items:
            items.append(text)
    return items if SUGGESTION_MIN <= len(items) <= SUGGESTION_MAX else None


async def suggest_follow_ups(questions: object) -> dict[str, Any]:
    normalized = normalize_suggestions(questions)
    if normalized is None:
        return {
            "status": "error",
            "code": "INVALID_SUGGESTIONS",
            "message": (
                f"서로 다른 한국어 질문 {SUGGESTION_MIN}~{SUGGESTION_MAX}개를 "
                f"각 1~{SUGGESTION_MAX_LENGTH}자로 넣어야 합니다. '특정 제품'처럼 대상을 비워 둔 질문은 "
                "제외되므로 결과에 나온 실제 대상이나 기준을 넣습니다."
            ),
        }
    return {"status": "ok", "count": len(normalized)}
