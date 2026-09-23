"""Production Planning Agent FastAPI application entry point."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from services.knowledge.documents import KnowledgeError
from fastapi.middleware.cors import CORSMiddleware

from api.routes_anthropic_proxy import router as anthropic_proxy_router
from api.routes_chat import router as chat_router
from api.routes_knowledge import router as knowledge_router
from api.routes_me import router as me_router
from api.routes_query_results import router as query_results_router
from core.config import CORS_ALLOW_ORIGINS
from services.results.store import cleanup_expired


logger = logging.getLogger("uvicorn.error")
RESULT_CLEANUP_INTERVAL_SECONDS = 60 * 60


async def _result_cleanup_loop() -> None:
    while True:
        try:
            deleted = cleanup_expired()
            if deleted:
                logger.info("조회 결과 정리 완료: deleted=%d", deleted)
        except Exception:
            logger.exception("조회 결과 정리 중 오류가 발생했습니다")
        await asyncio.sleep(RESULT_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """조회 결과 정리 태스크의 시작과 종료를 관리한다."""

    logger.info("조회 결과 정리 태스크를 시작합니다")
    cleanup_task = asyncio.create_task(_result_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        logger.info("조회 결과 정리 태스크를 종료했습니다")


app = FastAPI(
    title="Production Planning Agent API",
    lifespan=lifespan,
)

# 개발 환경의 Frontend dev 서버(Origin)만 허용한다.
# 과도하게 넓은 설정(allow_origins=["*"])은 사용하지 않는다.
# access scope 쿠키(pp_session_scope) 전달을 위해 credentials를 허용한다 —
# allow_origins가 명시적 목록인 한(와일드카드가 아닌 한) 안전하다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    chat_router,
    prefix="/api",
)

app.include_router(
    knowledge_router,
    prefix="/api",
)

app.include_router(
    me_router,
    prefix="/api",
)

app.include_router(
    query_results_router,
    prefix="/api",
)

# `/api` prefix가 없다 — Claude CLI가 ANTHROPIC_BASE_URL로 직접 참조하는 경로다
# (LLM_PROVIDER=local, `core.config.agent_provider_env()` 참고).
app.include_router(anthropic_proxy_router)


@app.get("/health")
async def health_check() -> dict:
    """Return backend health status."""
    return {"status": "ok"}


@app.exception_handler(KnowledgeError)
async def knowledge_error_handler(_request: Request, exc: KnowledgeError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message})
