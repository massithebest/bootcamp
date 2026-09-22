"""현재 요청 주체와 기능 플래그. 화면은 이 응답만 보고 버튼과 사용자 선택기를 켠다."""

from fastapi import APIRouter, Depends

from api.schemas import MeResponse
from core import config
from core.principal import AUTH_MODE, Principal, current_principal

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(current_principal)):
    stub = AUTH_MODE == "stub"
    return {
        "id": principal.id,
        "name": principal.name,
        "permissions": sorted(principal.permissions),
        "mode": AUTH_MODE,
        "knowledge_management": config.KNOWLEDGE_MANAGEMENT_ENABLED,
        "allow_self_approval": config.KNOWLEDGE_ALLOW_SELF_APPROVAL,
        # 스텁에서만 사용자 선택기를 보이도록 후보를 내려준다. 실제 인증에서는 비운다.
        "stub_users": [{"id": key, "name": entry["name"]} for key, entry in config.KNOWLEDGE_PRINCIPALS.items()] if stub else [],
    }
