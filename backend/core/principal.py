"""요청 주체(principal)와 권한 검사.

인증 체계가 생기기 전까지는 `X-User-Id` 헤더를 `KNOWLEDGE_PRINCIPALS` 설정과 대조하는
스텁이다. 이 값은 보안 경계가 아니며 작성자·승인자를 구분해 기록하기 위한 것이다.
실제 인증이 도입되면 `current_principal`만 교체하고 라우트는 `require(...)`만 쓴다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header

from core import config
from services.document_store import KnowledgeError


@dataclass(frozen=True)
class Principal:
    id: str
    name: str
    permissions: frozenset[str]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


#: 실제 인증으로 교체하면 "authenticated" 로 바꾼다. 화면은 이 값만 보고 사용자 선택기를 켠다.
AUTH_MODE = "stub"


def current_principal(x_user_id: str | None = Header(default=None)) -> Principal:
    principal_id = (x_user_id or "").strip() or config.KNOWLEDGE_DEFAULT_PRINCIPAL
    entry = config.KNOWLEDGE_PRINCIPALS.get(principal_id)
    if entry is None:
        raise KnowledgeError(403, "알 수 없는 사용자입니다.")
    return Principal(principal_id, entry["name"], frozenset(entry["permissions"]))


def require(permission: str) -> Callable[..., Principal]:
    """권한이 없으면 403을 내는 FastAPI 의존성을 만든다."""

    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if not config.KNOWLEDGE_MANAGEMENT_ENABLED:
            raise KnowledgeError(403, "지식 관리 기능이 꺼져 있습니다.")
        if not principal.can(permission):
            raise KnowledgeError(403, "이 작업을 수행할 권한이 없습니다.")
        return principal

    return dependency
