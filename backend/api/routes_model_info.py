"""입력창에 보여 줄 모델 표시 이름. deployment·provider 설정은 공개하지 않고 운영자가 정한 이름만 돌려준다."""

from fastapi import APIRouter

from api.schemas import ModelInfoResponse
from core import config

router = APIRouter(tags=["model-info"])


@router.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    return {"display_name": config.MODEL_DISPLAY_NAME}
