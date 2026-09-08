"""Production Planning Agent FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes_chat import router as chat_router
from core.config import CORS_ALLOW_ORIGINS


app = FastAPI(
    title="Production Planning Agent API",
)

# 개발 환경의 Frontend dev 서버(Origin)만 허용한다.
# 과도하게 넓은 설정(allow_origins=["*"])은 사용하지 않는다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat_router,
    prefix="/api",
)


@app.get("/health")
async def health_check() -> dict:
    """Return backend health status."""
    return {"status": "ok"}


# TODO:
# Claude Agent SDK에서 애플리케이션 단위 초기화가 필요한 경우
# FastAPI lifespan을 사용하여 추가한다.
