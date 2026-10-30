"""Economic calendar — real data only (pipatlas / faireconomy / FMP). No placeholders."""
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from loguru import logger
import pytz

from bot.config import get_settings

settings = get_settings()
_alerted_events: set[str] = set()


def _parse_event_dt(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            # handle trailing timezone like -04:00
            s = date_str.replace("Z", "+00:00")
            if fmt.endswith("%z") and len(s) >= 6 and s[-3] == ":":
                s = s[:-3] + s[-2:]
            return datetime.strptime(s[:26] if len(s) > 26 else s, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


async def _fetch_pipatlas() -> list:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get("https://pipatlas.com/api/calendar")
            if r.status_code == 200:
                data = r.json()
                return data.get("events") or data or []
    except Exception as e:
        logger.warning(f"pipatlas calendar: {e}")
    return []


async def _fetch_faireconomy() -> list:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return [
                        {
                            "name": e.get("title") or e.get("name") or "",
                            "currency": e.get("country") or e.get("currency") or "",
                            "impact": e.get("impact") or "Low",
                            "date": e.get("date") or "",
                            "forecast": e.get("forecast") or "",
                            "previous": e.get("previous") or "",
                            "actual": e.get("actual") or "",
                        }
                        for e in data
                    ]
    except Exception as e:
        logger.warning(f"faireconomy calendar: {e}")
    return []


async def _fetch_fmp(start: datetime, end: datetime) -> list:
    if not settings.fmp_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            url = (
                f"https://financialmodelingprep.com/api/v3/economic_calendar"
                f"?from={start.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}"
                f"&apikey={settings.fmp_api_key}"
            )
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "name": item.get("event") or "",
                        "currency": item.get("country") or "",
                        "impact": item.get("impact") or "Low",
                        "date": item.get("date") or "",
                        "forecast": item.get("estimate") or "",
                        "previous": item.get("previous") or "",
                        "actual": item.get("actual") or "",
                    }
                    for item in (data or [])
                ]
    except Exception as e:
        logger.warning(f"FMP calendar: {e}")
    return []


async def get_calendar_events(
    period: str = "today",
    timezone: str = "Europe/Moscow",
    lang: str = "ru",
) -> List[str]:
    """
    Fetch real economic calendar events.
    Returns formatted Telegram strings, or a clear unavailable message.
    Never returns invented placeholder events.
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "tomorrow":
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

    raw: list = []
    raw = await _fetch_pipatlas()
    if not raw:
        raw = await _fetch_faireconomy()
    if not raw:
        raw = await _fetch_fmp(start, end)

    if not raw:
        return [
            "⚠️ <b>Календарь временно недоступен</b>\n"
            "Источники Forex Factory / pipatlas не ответили.\n"
            "Попробуйте позже. Демо-события не показываются."
        ]

    events: List[str] = []
    for e in raw:
        name = e.get("name") or e.get("title") or ""
        if not name:
            continue
        date_str = e.get("date") or ""
        dt = _parse_event_dt(date_str)
        # filter by period when we can parse the date
        if dt is not None:
            try:
                if dt.tzinfo is None:
                    dt_local = tz.localize(dt)
                else:
                    dt_local = dt.astimezone(tz)
                if not (start <= dt_local < end):
                    # for week/today we still include if date parsing is ambiguous
                    if period in ("today", "tomorrow"):
                        continue
            except Exception:
                pass

        impact = e.get("impact") or ""
        currency = e.get("currency") or e.get("country") or ""
        actual = e.get("actual") or "—"
        forecast = e.get("forecast") or e.get("estimate") or "—"
        previous = e.get("previous") or "—"

        stars = (
            "⭐️⭐️⭐️"
            if str(impact).lower() in ("high", "red")
            else "⭐️⭐️"
            if str(impact).lower() in ("medium", "orange", "med")
            else "⭐️"
        )
        line = f"{stars} <b>{currency}</b> | {name}\n"
        line += f"🕒 {date_str}\n"
        line += (
            f"Actual: <code>{actual}</code>  "
            f"Forecast: <code>{forecast}</code>  "
            f"Prev: <code>{previous}</code>"
        )
        events.append(line)

    if not events:
        return [
            f"На период «{period}» подтверждённых событий в источниках нет.\n"
            "Это не ошибка — список пуст по реальным данным."
        ]

    return events[:50]


async def poll_calendar(bot) -> None:
    """Background: 15-min pre-alerts for high-impact events (real data only)."""
    logger.debug("Calendar poll tick")
    try:
        raw = await _fetch_pipatlas()
        if not raw:
            raw = await _fetch_faireconomy()
        if not raw:
            return

        now_utc = datetime.now(pytz.UTC)
        for e in raw:
            impact = str(e.get("impact") or "").lower()
            if impact not in ("high", "red"):
                continue
            name = e.get("name") or e.get("title") or ""
            date_str = e.get("date") or ""
            dt = _parse_event_dt(date_str)
            if not dt:
                continue
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            else:
                dt = dt.astimezone(pytz.UTC)

            delta = (dt - now_utc).total_seconds()
            # 15-min window: between 14 and 16 minutes before
            if 14 * 60 <= delta <= 16 * 60:
                key = f"{name}|{date_str}"
                if key in _alerted_events:
                    continue
                _alerted_events.add(key)
                currency = e.get("currency") or ""
                text = (
                    f"⏰ <b>15 мин до события</b>\n"
                    f"⭐️⭐️⭐️ <b>{currency}</b> | {name}\n"
                    f"🕒 {date_str}\n"
                    f"Forecast: <code>{e.get('forecast') or '—'}</code>  "
                    f"Prev: <code>{e.get('previous') or '—'}</code>"
                )
                try:
                    await bot.send_message(
                        chat_id=settings.admin_id,
                        text=text,
                        parse_mode="HTML",
                    )
                    logger.info(f"Calendar pre-alert: {name}")
                except Exception as ex:
                    logger.error(f"Calendar alert send error: {ex}")
    except Exception as e:
        logger.error(f"poll_calendar error: {e}")
