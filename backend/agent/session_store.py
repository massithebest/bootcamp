"""conversation_id <-> Claude Agent SDK session_id 매핑.

`conversation_id` 는 사용자 관점의 대화 식별자이고,
`session_id` 는 Claude Agent SDK 실행 Session 식별자로 서로 다른 개념이다.

현재는 프로세스 메모리에만 유지한다.

TODO:
- 다중 프로세스 / 재기동 대비가 필요하면 외부 저장소(Redis 등)로 교체한다.
"""

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


def clear() -> None:
    """테스트용: 매핑을 초기화한다."""

    _session_by_conversation.clear()
