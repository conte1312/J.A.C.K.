from __future__ import annotations

import asyncio
import unittest

from app.planning.scheduler import run_recurrence_scheduler


class _FakePlanningService:
    def __init__(self) -> None:
        self.calls = 0
        self.called = asyncio.Event()

    def generate_recurrence_instances(self) -> list[dict[str, object]]:
        self.calls += 1
        self.called.set()
        return []


class PlanningSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_scheduler_runs_immediately_and_can_be_cancelled(self) -> None:
        service = _FakePlanningService()
        scheduler = asyncio.create_task(
            run_recurrence_scheduler(service, interval_seconds=3600)
        )
        try:
            await asyncio.wait_for(service.called.wait(), timeout=1)
            self.assertEqual(service.calls, 1)
        finally:
            scheduler.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await scheduler


if __name__ == "__main__":
    unittest.main()
