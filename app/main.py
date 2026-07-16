from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.config import settings
# from app.core.dependencies import close_redis, init_redis
from app.core.logger import configure_logging, get_logger
# from app.core.security import ensure_rsa_keys
# from app.database.session import dispose_engine
# from app.exceptions import register_exception_handlers
from app.routers import (
    employee_router
    )
from app.database.init_db import init_db,dispose_db

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # configure_logging()
    log.info("Starting %s (env=%s)", settings.APP_NAME, settings.ENV)

    # # Keys are minted automatically on first boot — prod-safe and idempotent.
    # ensure_rsa_keys()
    # await init_redis()
    await init_db() 
    log.info("%s ready on port %s", settings.APP_NAME, settings.APP_PORT)
    yield

    # await close_redis()
    await dispose_db()
    log.info("%s shut down cleanly", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url="/docs" if not settings.is_prod else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(employee_router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )