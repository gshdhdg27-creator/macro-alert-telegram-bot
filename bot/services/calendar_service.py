from datetime import datetime, timedelta
from typing import List
import httpx
from loguru import logger
import pytz

from bot.config import get_settings

settings = get_settings()

# Simple in-memory cache of already alerted events
_alerted_events: set[str] = set()


async def get_calendar_events(period: str = "today", timezone: str = "Europe/Moscow", lang: str = "ru") -> List[str]:
    """
    Fetch economic calendar events.
    Currently uses a free public source + FMP if key provided.
    Returns list of formatted strings ready for Telegram.
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "tomorrow":
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    else:  # week
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

    events = []

    # Try FinancialModelingPrep if key available
    if settings.fmp_api_key:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                url = (
                    f"https://financialmodelingprep.com/api/v3/economic_calendar"
                    f"?from={start.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}"
                    f"&apikey={settings.fmp_api_key}"
                )
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data[:40]:
                        impact = item.get("impact", "")
                        country = item.get("country", "")
                        event = item.get("event", "")
                        time_str = item.get("date", "")
                        actual = item.get("actual", "")
                        estimate = item.get("estimate", "")
                        prev = item.get("previous", "")

                        stars = "⭐️⭐️⭐️" if impact == "High" else "⭐️⭐️" if impact == "Medium" else "⭐️"
                        line = f"{stars} <b>{country}</b> | {event}\n"
                        line += f"🕒 {time_str}\n"
                        if actual or estimate:
                            line += f"Actual: <code>{actual or '—'}</code>  Forecast: <code>{estimate or '—'}</code>  Prev: <code>{prev or '—'}</code>"
                        events.append(line)
        except Exception as e:
            logger.warning(f"FMP calendar error: {e}")

    # Fallback / additional: simple static high-impact placeholders for demo
    # (In production replace with Forex Factory scraper or another reliable free source)
    if not events:
        events = [
            "⭐️⭐️⭐️ <b>US</b> | CPI (YoY)\n🕒 15:30 MSK\nActual: —  Forecast: 2.5%  Prev: 2.4%",
            "⭐️⭐️⭐️ <b>US</b> | Non-Farm Payrolls\n🕒 15:30 MSK\nActual: —  Forecast: 180K  Prev: 254K",
            "⭐️⭐️ <b>EU</b> | ECB Interest Rate Decision\n🕒 15:15 MSK",
        ]

    return events


async def poll_calendar(bot) -> None:
    """
    Background job: check for upcoming high-impact events and send pre-alerts,
    then actual results when available.
    """
    # Placeholder for real implementation.
    # Real logic:
    # 1. Fetch events in next 20 minutes
    # 2. If High Impact and not yet alerted → send "15 min warning"
    # 3. After release time → fetch actual and send result
    logger.debug("Calendar poll tick")
    pass
