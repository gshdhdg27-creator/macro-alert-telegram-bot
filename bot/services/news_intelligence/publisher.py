"""Publish analyzed news to Telegram admin — no spam, dedupe."""
from __future__ import annotations

from typing import Set

from aiogram import Bot
from loguru import logger
from sqlalchemy import select

from bot.config import get_settings
from bot.models.db import UserSettings, AlertHistory, async_session
from bot.services.news_intelligence.analyzer import analyze
from bot.services.news_intelligence.classifier import classify
from bot.services.news_intelligence.collector import collect_from_rss
from bot.services.news_intelligence.formatter import format_news_message, news_inline_kb

settings = get_settings()
_seen: Set[str] = set()


async def process_and_publish(bot: Bot, max_publish: int = 3) -> int:
    """Collect → classify → analyze → publish top items. Returns count sent."""
    raw_list = collect_from_rss()
    published = 0
    raw_list.sort(key=lambda x: x.published or x.title, reverse=True)

    for item in raw_list:
        if item.id in _seen:
            continue
        _seen.add(item.id)
        if len(_seen) > 8000:
            _seen.clear()

        category, assets = classify(item)
        analysis = await analyze(item, category, assets)
        importance = analysis.get("importance", "MEDIUM")
        if importance not in ("MEDIUM", "HIGH", "CRITICAL"):
            continue

        text = format_news_message(
            item,
            analysis,
            pub_type="BREAKING NEWS" if importance == "CRITICAL" else "MARKET NEWS",
        )
        kb = news_inline_kb(item, category)

        async with async_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == settings.admin_id)
            )
            user = result.scalar_one_or_none()
            if user and user.quiet_mode:
                logger.info("Quiet mode — skip publish")
                return published
            if user and user.only_high_impact and importance not in ("HIGH", "CRITICAL"):
                continue

        try:
            if item.image:
                try:
                    await bot.send_photo(
                        chat_id=settings.admin_id,
                        photo=item.image,
                        caption=text[:1024],
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                except Exception:
                    await bot.send_message(
                        chat_id=settings.admin_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                        disable_web_page_preview=False,
                    )
            else:
                await bot.send_message(
                    chat_id=settings.admin_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    disable_web_page_preview=False,
                )

            async with async_session() as session:
                session.add(
                    AlertHistory(
                        user_id=settings.admin_id,
                        alert_type="news_intel",
                        asset_tags=",".join(assets),
                        title=item.title[:500],
                        body=text[:4000],
                        importance=importance.lower(),
                        raw_data={"link": item.link, "source": item.source, "category": category},
                    )
                )
                await session.commit()

            published += 1
            logger.info(f"Published [{importance}] {item.title[:60]}")
            if published >= max_publish:
                break
        except Exception as e:
            logger.error(f"Publish error: {e}")

    return published


async def get_category_news(category: str, limit: int = 5) -> list:
    """On-demand category feed for user buttons."""
    raw_list = collect_from_rss(max_per_feed=12)
    out = []
    for item in raw_list:
        cat, assets = classify(item)
        if cat != category and category != "all":
            from bot.services.news_intelligence.categories import CATEGORIES
            text = f"{item.title} {item.summary}".lower()
            kws = CATEGORIES.get(category, {}).get("keywords") or []
            if not any(k in text for k in kws):
                continue
        analysis = await analyze(item, category if category != "all" else cat, assets)
        out.append((item, analysis))
        if len(out) >= limit:
            break
    return out
