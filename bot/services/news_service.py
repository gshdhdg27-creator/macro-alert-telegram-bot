"""Background news poll — Trading AI News Intelligence."""
from loguru import logger

from bot.services.news_intelligence.publisher import process_and_publish


async def poll_news(bot) -> None:
    """Scheduler job: collect, analyze, publish real news only."""
    logger.debug("News intelligence poll tick")
    try:
        n = await process_and_publish(bot, max_publish=2)
        if n:
            logger.info(f"News intelligence published {n} item(s)")
    except Exception as e:
        logger.error(f"News intelligence poll error: {e}")
