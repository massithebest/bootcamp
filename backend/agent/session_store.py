"""conversation_id <-> Claude Agent SDK session_id 매핑, turn_id -> 포크 지점.

`conversation_id` 는 사용자 관점의 대화 식별자이고,
`session_id` 는 Claude Agent SDK 실행 Session 식별자로 서로 다른 개념이다.
`turn_id` 는 완료된 턴(사용자 질문 하나 + 어시스턴트 응답 하나) 하나를
가리키는 식별자로, 편집/재생성이 "이 턴 직전까지" 를 포크 지점으로 쓴다.

현재는 프로세스 메모리에만 유지한다.

TODO:
- 다중 프로세스 / 재기동 대비가 필요하면 외부 저장소(Redis 등)로 교체한다.
"""

from dataclasses import dataclass


_session_by_conversation: dict[str, str] = {}


def get_session_id(conversation_id: str | None) -> str | None:
    """대화에 연결된 SDK session_id 를 반환한다. (없으면 None)"""

    if conversation_id is None:
        return None
    return _session_by_conversation.get(conversation_id)


def bind_session_id(conversation_id: str | None, session_id: str | None) -> None:
    """대화와 SDK session_id 를 연결한다."""

    if conversation_id is None or session_id is None:
        return
    _session_by_conversation[conversation_id] = session_id


@dataclass(frozen=True)
class TurnAnchor:
    """한 턴이 끝난 시점의 포크 지점.

    `session_id` 를 `resume` 하되 `fork_session=True` 로 새 session_id 를
    받고, `last_entry_uuid` 를 `resume_session_at` 에 넘겨 그 지점까지만
    이력을 적재한다 (agent/agent.py 참고).
    """

    session_id: str
    last_entry_uuid: str | None


_turn_anchors: dict[str, TurnAnchor] = {}


def record_turn_anchor(
    turn_id: str, session_id: str, last_entry_uuid: str | None
) -> None:
    """완료된 턴의 포크 지점을 기록한다. 이후 편집/재생성이 여기서 갈라진다."""

    _turn_anchors[turn_id] = TurnAnchor(
        session_id=session_id, last_entry_uuid=last_entry_uuid
    )


def get_turn_anchor(turn_id: str) -> TurnAnchor | None:
    """`turn_id` 의 포크 지점을 반환한다. (없으면 None — 호출 측이 새 대화로 폴백)"""

    return _turn_anchors.get(turn_id)


def clear() -> None:
    """테스트용: 매핑을 초기화한다."""

    _session_by_conversation.clear()
    _turn_anchors.clear()
