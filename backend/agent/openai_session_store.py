"""OpenAI 실행부의 대화 기록과 편집/재생성 분기 지점.

Claude 실행부는 SDK session 을 `resume`·`fork_session`으로 이어 쓰지만, OpenAI Agents SDK
실행부는 성공한 턴이 끝난 시점의 전체 입력 기록(`RunResult.to_input_list()`)을 직접 보관한다.

- conversation_id -> 최신 기록: 평범한 다음 턴이 이어 쓴다.
- turn_id -> 그 턴 직후 기록: 편집/재생성이 여기서 새 갈래를 만든다(원본 기록은 바꾸지 않음).

기록은 같은 갈래에서 앞부분 item 객체를 공유하는 tuple 로 둔다. 대화마다 분기 지점을
`MAX_TURNS_PER_CONVERSATION`개까지만 보관하고, 넘치면 오래된 turn_id 부터 지운다(그 turn_id 로
분기하면 새 대화 경고). 현재는 프로세스 메모리에만 유지한다(`session_store`와 같음).
"""

from collections import deque
from typing import Any


#: 대화 하나에서 편집/재생성 분기 지점으로 보관하는 최근 턴 수.
MAX_TURNS_PER_CONVERSATION = 50

#: 알 수 없거나 보관 기간이 지난 turn_id 로 분기할 때의 경고(Claude 실행부와 같은 문구).
FORK_FALLBACK_MESSAGE = "이전 응답 지점을 찾을 수 없어 새 대화로 시작합니다."

_latest_by_conversation: dict[str, tuple[Any, ...]] = {}
_snapshot_by_turn: dict[str, tuple[Any, ...]] = {}
_turns_by_conversation: dict[str | None, deque[str]] = {}


def latest_history(conversation_id: str | None) -> list[Any]:
    """대화의 최신 기록. 없으면 빈 목록."""

    if conversation_id is None:
        return []
    return list(_latest_by_conversation.get(conversation_id, ()))


def turn_history(turn_id: str) -> list[Any] | None:
    """`turn_id` 직후의 기록. 없으면 None — 호출 측이 새 대화로 폴백한다."""

    snapshot = _snapshot_by_turn.get(turn_id)
    return None if snapshot is None else list(snapshot)


def record_turn(conversation_id: str | None, turn_id: str, history: list[Any]) -> None:
    """성공한 턴의 기록을 대화의 최신 기록과 분기 지점으로 남긴다."""

    snapshot = tuple(history)
    if conversation_id is not None:
        _latest_by_conversation[conversation_id] = snapshot
    _snapshot_by_turn[turn_id] = snapshot
    turns = _turns_by_conversation.setdefault(conversation_id, deque())
    turns.append(turn_id)
    while len(turns) > MAX_TURNS_PER_CONVERSATION:
        _snapshot_by_turn.pop(turns.popleft(), None)


def clear() -> None:
    """테스트용: 기록을 초기화한다."""

    _latest_by_conversation.clear()
    _snapshot_by_turn.clear()
    _turns_by_conversation.clear()
