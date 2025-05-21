from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings


scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE_LOCAL)
