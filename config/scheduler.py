from os import getenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler(timezone=getenv("TIMEZONE_LOCAL"))
