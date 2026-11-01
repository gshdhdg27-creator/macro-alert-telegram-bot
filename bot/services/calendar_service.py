"""Economic calendar — real data only. HTML-escaped Telegram output. DB-backed alert dedupe."""
from __future__ import annotations

import hashlib
import html
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import httpx
import pytz
from loguru import logger
from sqlalchemy import select

from bot.config import get_settings
from bot.models.db import CalendarAlert, CalendarEventState, async_session

settings = get_settings()


def _e(s) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def stable_event_id(name: str, date_str: str, currency: str = "") -> str:
    raw = f"{name.strip()}|{date_str.strip()}|{currency.strip()}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


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


def _has_actual(value) -> bool:
    if value is None:
        return False
    s = str(value).strip()
    return bool(s) and s not in ("—", "-", "n/a", "N/A", "")


def _norm_actual(value) -> str:
    if not _has_actual(value):
        return ""
    return str(value).strip()


async def _fetch_pipatlas() -> list:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get("https://pipatlas.com/api/calendar")
            if r.status_code == 200:
                data = r.json()
                events = data.get("events") or data or []
                for e in events:
                    e["_provider"] = "pipatlas"
                return events
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
                            "_provider": "faireconomy/FF feed",
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
                        "_provider": "FMP",
                    }
                    for item in (data or [])
                ]
    except Exception as e:
        logger.warning(f"FMP calendar: {e}")
    return []


async def fetch_calendar_raw() -> list:
    raw = await _fetch_faireconomy()
    if not raw:
        raw = await _fetch_pipatlas()
    if not raw:
        now = datetime.utcnow()
        raw = await _fetch_fmp(now, now + timedelta(days=7))
    return raw


async def get_calendar_events(
    period: str = "today",
    timezone: str = "Europe/Moscow",
    lang: str = "ru",
) -> List[str]:
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

    raw = await fetch_calendar_raw()
    if not raw:
        return [
            "⚠️ <b>Календарь временно недоступен</b>\n"
            "Источники не ответили.\n"
            "Попробуйте позже. Демо-события не показываются."
        ]

    events: List[str] = []
    for e in raw:
        name = e.get("name") or e.get("title") or ""
        if not name:
            continue
        date_str = e.get("date") or ""
        dt = _parse_event_dt(date_str)
        if dt is not None:
            try:
                if dt.tzinfo is None:
                    dt_local = tz.localize(dt)
                else:
                    dt_local = dt.astimezone(tz)
                if period in ("today", "tomorrow") and not (start <= dt_local < end):
                    continue
            except Exception:
                pass

        impact = e.get("impact") or ""
        currency = e.get("currency") or e.get("country") or ""
        actual = e.get("actual") or "—"
        forecast = e.get("forecast") or e.get("estimate") or "—"
        previous = e.get("previous") or "—"
        provider = e.get("_provider") or "calendar"

        stars = (
            "⭐️⭐️⭐️"
            if str(impact).lower() in ("high", "red")
            else "⭐️⭐️"
            if str(impact).lower() in ("medium", "orange", "med")
            else "⭐️"
        )
        line = f"{stars} <b>{_e(currency)}</b> | {_e(name)}\n"
        line += f"🕒 {_e(date_str)} · {_e(provider)}\n"
        line += (
            f"Actual: <code>{_e(actual)}</code>  "
            f"Forecast: <code>{_e(forecast)}</code>  "
            f"Prev: <code>{_e(previous)}</code>"
        )
        events.append(line)

    if not events:
        return [
            f"На период «{_e(period)}» подтверждённых событий нет.\n"
            "Это не ошибка — список пуст по реальным данным."
        ]
    return events[:50]


async def _already_alerted(event_id: str, kind: str) -> bool:
    async with async_session() as session:
        r = await session.execute(
            select(CalendarAlert.id).where(
                CalendarAlert.event_id == event_id,
                CalendarAlert.alert_kind == kind,
            ).limit(1)
        )
        return r.scalar_one_or_none() is not None


async def _mark_alerted(event_id: str, kind: str, title: str) -> None:
    async with async_session() as session:
        try:
            session.add(CalendarAlert(event_id=event_id, alert_kind=kind, title=(title or "")[:500]))
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning(f"calendar dedupe mark failed: {e}")


async def _get_event_state(event_id: str) -> Optional[CalendarEventState]:
    async with async_session() as session:
        r = await session.execute(
            select(CalendarEventState).where(CalendarEventState.event_id == event_id).limit(1)
        )
        return r.scalar_one_or_none()


async def _upsert_event_state(event_id: str, actual_norm: str) -> None:
    async with async_session() as session:
        try:
            r = await session.execute(
                select(CalendarEventState).where(CalendarEventState.event_id == event_id).limit(1)
            )
            row = r.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if row:
                row.last_actual = actual_norm or None
                row.observed_at = now
            else:
                session.add(
                    CalendarEventState(
                        event_id=event_id,
                        last_actual=actual_norm or None,
                        observed_at=now,
                    )
                )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning(f"event state upsert failed: {e}")


async def _should_notify_actual(event_id: str, actual_raw) -> Tuple[bool, str]:
    """
    First observation: establish baseline, never notify.
    Later: notify only if previous was empty and now populated,
    or previous populated value genuinely changed (revision).
    """
    current = _norm_actual(actual_raw)
    state = await _get_event_state(event_id)

    if state is None:
        # Baseline — record and skip alert
        await _upsert_event_state(event_id, current)
        return False, current

    prev = (state.last_actual or "").strip()

    if not prev and current:
        # missing → populated
        return True, current

    if prev and current and prev != current:
        # revision of Actual (rare but real)
        return True, current

    # unchanged or still empty
    await _upsert_event_state(event_id, current)
    return False, current


async def poll_calendar(bot) -> None:
    """15-min pre-alerts + actual-release (only missing→populated after baseline)."""
    logger.debug("Calendar poll tick")
    try:
        from bot.services.alert_service import send_alert_to_user

        raw = await fetch_calendar_raw()
        if not raw:
            return

        now_utc = datetime.now(pytz.UTC)
        for e in raw:
            impact = str(e.get("impact") or "").lower()
            name = e.get("name") or e.get("title") or ""
            date_str = e.get("date") or ""
            currency = e.get("currency") or e.get("country") or ""
            if not name:
                continue

            eid = stable_event_id(name, date_str, currency)
            actual = e.get("actual")
            forecast = e.get("forecast") or e.get("estimate") or "—"
            previous = e.get("previous") or "—"

            # --- Actual release tracking (high impact) ---
            if impact in ("high", "red"):
                should, current = await _should_notify_actual(eid, actual)
                if should and current:
                    if not await _already_alerted(eid, "actual"):
                        text = (
                            f"📢 <b>Actual released</b>\n"
                            f"⭐️⭐️⭐️ <b>{_e(currency)}</b> | {_e(name)}\n"
                            f"🕒 {_e(date_str)}\n"
                            f"Actual: <code>{_e(current)}</code>  "
                            f"Forecast: <code>{_e(forecast)}</code>  "
                            f"Prev: <code>{_e(previous)}</code>\n"
                            f"<i>Сравнение с прогнозом показано как есть. "
                            f"Рыночная реакция не выдумана.</i>"
                        )
                        ok = await send_alert_to_user(
                            bot,
                            alert_type="calendar_actual",
                            title=f"Actual: {name}"[:200],
                            body=text,
                            asset_tags=currency,
                            importance="high",
                            raw_data={"event_id": eid, "actual": current},
                        )
                        if ok:
                            await _mark_alerted(eid, "actual", name)
                            await _upsert_event_state(eid, current)
                            logger.info(f"Calendar actual alert: {name}")
                    else:
                        await _upsert_event_state(eid, current)
                elif current:
                    await _upsert_event_state(eid, current)

            # --- 15-min pre-alert ---
            if impact not in ("high", "red"):
                continue
            dt = _parse_event_dt(date_str)
            if not dt:
                continue
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            else:
                dt = dt.astimezone(pytz.UTC)

            delta = (dt - now_utc).total_seconds()
            if not (14 * 60 <= delta <= 16 * 60):
                continue
            if await _already_alerted(eid, "pre15"):
                continue

            text = (
                f"⏰ <b>15 мин до события</b>\n"
                f"⭐️⭐️⭐️ <b>{_e(currency)}</b> | {_e(name)}\n"
                f"🕒 {_e(date_str)}\n"
                f"Forecast: <code>{_e(forecast)}</code>  "
                f"Prev: <code>{_e(previous)}</code>"
            )
            ok = await send_alert_to_user(
                bot,
                alert_type="calendar_pre15",
                title=f"15m: {name}"[:200],
                body=text,
                asset_tags=currency,
                importance="high",
                raw_data={"event_id": eid, "date": date_str},
            )
            if ok:
                await _mark_alerted(eid, "pre15", name)
                logger.info(f"Calendar pre-alert: {name}")
    except Exception as e:
        logger.error(f"poll_calendar error: {e}")
