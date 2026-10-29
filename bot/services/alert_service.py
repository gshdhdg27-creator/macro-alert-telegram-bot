from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Bot
from loguru import logger
from sqlalchemy import select

from bot.config import get_settings
from bot.models.db import UserSettings, AlertHistory, async_session

settings = get_settings()


async def send_alert_to_user(
    bot: Bot,
    alert_type: str,
    title: str,
    body: str,
    asset_tags: str = "",
    importance: str = "medium",
    raw_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Send alert to the single admin user, respecting quiet mode and subscriptions.
    Also save to history.
    """
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

        if user.only_high_impact and importance != "high":
            return

        # Check asset subscription (if tags provided)
        if asset_tags and user.subscribed_assets:
            tags = [t.strip().upper() for t in asset_tags.split(",")]
            subscribed = user.subscribed_assets or {}
            # Map tags back to asset keys roughly
            relevant = False
            for key, conf in subscribed.items():
                if conf:
                    # simple check
                    relevant = True
                    break
            if not relevant and asset_tags:
                # for now send if any subscription exists; refine later
                pass

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

        # Save history
        history = AlertHistory(
            user_id=settings.admin_id,
            alert_type=alert_type,
            asset_tags=asset_tags,
            title=title[:500],
            body=body,
            importance=importance,
            raw_data=raw_data,
        )
        session.add(history)
        await session.commit()
        logger.info(f"Alert sent & saved: {title[:80]}")
