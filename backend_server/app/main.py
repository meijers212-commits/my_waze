import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.basket_routes import router as basket_router
from app.api.products_routes import router as products_router
from app.api.receipt_routes import router as receipt_router
from app.api.sync_routes import router as sync_router
from app.core.config import settings
from app.core.constants import LOG_FILE_BACKUP_COUNT, LOG_FILE_MAX_BYTES
from app.core.scheduler import start_scheduler, stop_scheduler
from app.database.base import Base
from app.database.session import SessionLocal, engine
import app.models  # noqa: F401


def configure_logging() -> None:
    log_file_path: Path = settings.log_file_path
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format)

    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


configure_logging()
logger = logging.getLogger(__name__)


def _weekly_sync_job() -> None:
    """Scheduled job: runs weekly price sync inside its own DB session."""
    from app.services.sync_service import SyncService  # noqa: PLC0415

    db = SessionLocal()
    try:
        SyncService().run_sync(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created on startup.")

    start_scheduler(_weekly_sync_job)
    logger.info("Application startup completed.")

    yield

    stop_scheduler()
    logger.info("Application shutdown completed.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(receipt_router)
app.include_router(basket_router)
app.include_router(products_router)
app.include_router(sync_router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
