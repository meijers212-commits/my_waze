from __future__ import annotations

import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

SYNC_JOB_ID = "hourly_price_sync"

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler  # noqa: PLW0603
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")
    return _scheduler


def start_scheduler(sync_job: Callable[[], None]) -> None:
    """Register the hourly sync job and start the background scheduler."""
    scheduler = get_scheduler()

    scheduler.add_job(
        sync_job,
        trigger=IntervalTrigger(hours=1, timezone="Asia/Jerusalem"),
        id=SYNC_JOB_ID,
        name="Hourly Price Sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    if not scheduler.running:
        scheduler.start()

    logger.info("Scheduler started. Hourly price sync registered.")


def stop_scheduler() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
