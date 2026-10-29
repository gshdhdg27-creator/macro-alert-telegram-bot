import feedparser
from datetime import datetime, timezone
from loguru import logger
from typing import List, Dict

from bot.services.ai_filter import filter_and_summarize
from bot.services.alert_service import send_alert_to_user
from bot.config import get_settings

settings = get_settings()

# Free high-quality RSS sources
RSS_FEEDS = [
    "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    # Add more reliable RSS as needed
]

_seen_guids: set[str] = set()


async def poll_news(bot) -> None:
    """
    Background job: poll RSS feeds, filter with AI, send alerts.
    """
    logger.debug("News poll tick")

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                guid = entry.get("id") or entry.get("link") or entry.get("title")
                if not guid or guid in _seen_guids:
                    continue

                _seen_guids.add(guid)
                # Keep set from growing forever
                if len(_seen_guids) > 5000:
                    _seen_guids.clear()

                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                link = entry.get("link", "")

                result = await filter_and_summarize(title, summary, source=feed_url)

                if result and result.get("important"):
                    tags = result.get("tags", [])
                    importance = result.get("importance", "medium")

                    # Format message
                    tag_str = " ".join(f"#{t}" for t in tags)
                    body = result.get("summary_ru") or result.get("summary_en") or title

                    text = (
                        f"🚨 <b>BREAKING NEWS</b> | {tag_str}\n\n"
                        f"{body}\n\n"
                        f"<a href=\"{link}\">Источник</a>"
                    )

                    await send_alert_to_user(
                        bot=bot,
                        alert_type="breaking",
                        title=title,
                        body=text,
                        asset_tags=",".join(tags),
                        importance=importance,
                        raw_data={"link": link, "source": feed_url},
                    )

        except Exception as e:
            logger.warning(f"RSS poll error ({feed_url}): {e}")
