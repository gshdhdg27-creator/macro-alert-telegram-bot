"""Send alerts respecting quiet mode, importance, and asset subscriptions."""
from typing import Optional, Dict, Any

from aiogram import Bot
from loguru import logger
from sqlalchemy import select

from bot.config import get_settings, ASSETS
from bot.models.db import UserSettings, AlertHistory, async_session

settings = get_settings()


def _tags_match_subscriptions(asset_tags: str, subscribed: dict) -> bool:
    """
    Return True if alert is relevant to user subscriptions.
    Empty tags → broadcast (calendar/global).
    """
    if not asset_tags:
        return True
    if not subscribed:
        return True

    tags = {t.strip().upper() for t in asset_tags.split(",") if t.strip()}
    if not tags:
        return True

    for key, enabled in (subscribed or {}).items():
        if not enabled:
            continue
        conf = ASSETS.get(key) or {}
        conf_tags = {str(t).upper() for t in (conf.get("tags") or [])}
        conf_tags.add(key.upper())
        name = (conf.get("name_en") or conf.get("name_ru") or "").upper()
        if tags & conf_tags:
            return True
        if any(t in name for t in tags):
            return True
    return False


async def send_alert_to_user(
    bot: Bot,
    alert_type: str,
    title: str,
    body: str,
    asset_tags: str = "",
    importance: str = "medium",
    raw_data: Optional[Dict[str, Any]] = None,
) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == settings.admin_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("No user settings found for admin")
            return

        if user.quiet_mode:
            logger.info("Quiet mode active — alert suppressed")
            return

        imp = (importance or "medium").lower()
        if user.only_high_impact and imp not in ("high", "critical"):
            return

        if not _tags_match_subscriptions(asset_tags, user.subscribed_assets or {}):
            logger.info(f"Alert skipped — not in subscriptions: {asset_tags}")
            return

        try:
            await bot.send_message(
                chat_id=settings.admin_id,
                text=body,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return

        history = AlertHistory(
            user_id=settings.admin_id,
            alert_type=alert_type,
            asset_tags=asset_tags,
            title=title[:500],
            body=body,
            importance=imp,
            raw_data=raw_data,
        )
        session.add(history)
        await session.commit()
        logger.info(f"Alert sent & saved: {title[:80]}")
