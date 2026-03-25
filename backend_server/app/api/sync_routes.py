from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from app.services.sync_service import SyncResult

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger(__name__)

_last_result: SyncResult | None = None
_is_running: bool = False


def _run_sync_background() -> None:
    """Background task: creates its own DB session for the full sync run."""
    global _last_result, _is_running  # noqa: PLW0603

    if _is_running:
        logger.warning("Sync already running — skipping duplicate trigger.")
        return

    _is_running = True
    try:
        from app.database.session import SessionLocal  # noqa: PLC0415
        from app.services.sync_service import SyncService  # noqa: PLC0415

        db = SessionLocal()
        try:
            _last_result = SyncService().run_sync(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Unhandled error during background sync")
    finally:
        _is_running = False


@router.post("/trigger", summary="Trigger a price sync immediately (runs in background)")
def trigger_sync(background_tasks: BackgroundTasks) -> dict:
    if _is_running:
        return {"status": "already_running"}
    background_tasks.add_task(_run_sync_background)
    return {"status": "started", "triggered_at": datetime.utcnow().isoformat() + "Z"}


@router.get("/status", summary="Get the result of the last sync run")
def sync_status() -> dict:
    if _is_running:
        return {"status": "running"}
    if _last_result is None:
        return {"status": "never_run"}
    return {"status": "completed", **_last_result.to_dict()}
