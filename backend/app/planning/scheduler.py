from __future__ import annotations

import asyncio
import logging
import sqlite3

from app.planning.service import PlanningService

logger = logging.getLogger("jack.backend.planning.scheduler")

RECURRENCE_SCAN_INTERVAL_SECONDS = 60 * 60


async def run_recurrence_scheduler(
    service: PlanningService,
    interval_seconds: int = RECURRENCE_SCAN_INTERVAL_SECONDS,
) -> None:
    while True:
        try:
            created = service.generate_recurrence_instances()
            if created:
                logger.info("Generated %d recurring task instance(s)", len(created))
        except sqlite3.Error:
            logger.exception("Recurring task generation failed")
        await asyncio.sleep(interval_seconds)
