"""FastAPI-приложение мок-сервера 1С (standalone, D-01)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from onec_mock.config import settings

logger = logging.getLogger("onec_mock")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=settings.log_level)
    logger.info("onec-mock starting (schema=%s)", settings.onec_mock_schema)
    from onec_mock.db import async_session, init_db
    from onec_mock.scheduler import SyncScheduler
    from onec_mock.seed import seed_catalog

    await init_db()
    if settings.seed_on_start:
        async with async_session() as session:
            await seed_catalog(session, settings)
    sync_scheduler = SyncScheduler(settings)
    sync_scheduler.start()
    app.state.sync_scheduler = sync_scheduler
    yield
    sync_scheduler.shutdown()
    logger.info("onec-mock stopped")


app = FastAPI(title="1C Mock Server", lifespan=lifespan)

from onec_mock.api import router as control_router  # noqa: E402

app.include_router(control_router)


@app.get("/health/")
async def health() -> dict:
    return {"status": "ok"}
