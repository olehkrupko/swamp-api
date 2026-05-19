"""Scheduler configuration for async background tasks.

Provides a global AsyncIOScheduler instance configured with the
application's local timezone for scheduling periodic parsing and updates.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings


# Global scheduler instance for managing background tasks
scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE_LOCAL)
