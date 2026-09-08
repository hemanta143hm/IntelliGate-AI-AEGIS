"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import PROJECT_ROOT, settings
from app.core.logging_config import configure_logging
from app.database.db import initialize_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    initialize_database()
    logger.info("AEGIS application started")
    yield
    logger.info("AEGIS application stopped")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "frontend" / "static"), name="static")
app.include_router(router)
