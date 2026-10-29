import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from bot.config import get_settings
from bot.models.db import init_db
from bot.handlers import start, menu, settings as settings_handler, calendar, history
from bot.services.calendar_service import poll_calendar
from bot.services.news_service import poll_news

# Ensure data dir exists
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

settings = get_settings()

# Logging
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)
logger.add(
    "logs/bot.log",
    rotation="10 MB",
    retention="30 days",
    level=settings.log_level,
)


async def main() -> None:
    logger.info("Starting Macro Alert Bot v1.0.0")

    await init_db()
    logger.info("Database initialized")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Routers
    dp.include_router(start.router)
    dp.include_router(settings_handler.router)
    dp.include_router(calendar.router)
    dp.include_router(history.router)
    dp.include_router(menu.router)  # menu last because of broad F.text

    # Scheduler
    scheduler = AsyncIOScheduler(timezone=settings.default_timezone)
    scheduler.add_job(poll_calendar, "interval", seconds=settings.calendar_poll_interval, args=[bot])
    scheduler.add_job(poll_news, "interval", seconds=settings.news_poll_interval, args=[bot])
    scheduler.start()
    logger.info("Scheduler started")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
