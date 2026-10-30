"""Publish analyzed news to Telegram — DB dedupe, full text + optional photo."""
from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot
from loguru import logger
from sqlalchemy import select

from bot.config import get_settings
from bot.models.db import UserSettings, AlertHistory, PublishedNews, async_session
from bot.services.news_intelligence.analyzer import analyze
from bot.services.news_intelligence.classifier import classify
from bot.services.news_intelligence.collector import collect_from_rss, RawNews
from bot.services.news_intelligence.formatter import format_news_message, news_inline_kb

settings = get_settings()


def _sort_key(item: RawNews):
    if item.published is not None:
        return (0, item.published)
    return (1, datetime.min.replace(tzinfo=timezone.utc))


async def _already_published(news_id: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(PublishedNews.id).where(PublishedNews.news_id == news_id).limit(1)
        )
        return result.scalar_one_or_none() is not None


async def _mark_published(item: RawNews, category: str) -> None:
    async with async_session() as session:
        try:
            session.add(
                PublishedNews(
                    news_id=item.id,
                    title=(item.title or "")[:500],
                    source=item.source,
                    link=item.link,
                    category=category,
                )
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning(f"dedupe mark failed: {e}")


async def process_and_publish(bot: Bot, max_publish: int = 2) -> int:
    raw_list = collect_from_rss()
    published = 0
    raw_list.sort(key=_sort_key, reverse=True)

    for item in raw_list:
        try:
            if await _already_published(item.id):
                continue

            category, assets = classify(item)
            analysis = await analyze(item, category, assets)
            importance = analysis.get("importance", "MEDIUM")
            if importance not in ("MEDIUM", "HIGH", "CRITICAL"):
                await _mark_published(item, category)
                continue

            async with async_session() as session:
                result = await session.execute(
                    select(UserSettings).where(UserSettings.user_id == settings.admin_id)
                )
                user = result.scalar_one_or_none()
                if user and user.quiet_mode:
                    logger.info("Quiet mode — skip publish")
                    return published
                if user and user.only_high_impact and importance not in ("HIGH", "CRITICAL"):
                    await _mark_published(item, category)
                    continue

            text = format_news_message(
                item,
                analysis,
                pub_type="BREAKING NEWS" if importance == "CRITICAL" else "MARKET NEWS",
            )
            kb = news_inline_kb(item, category)

            # Photo separately: never silently truncate full analysis into caption
            try:
                if item.image and item.image.startswith("https://"):
                    try:
                        await bot.send_photo(
                            chat_id=settings.admin_id,
                            photo=item.image,
                            caption=None,
                        )
                    except Exception as pe:
                        logger.debug(f"photo skip: {pe}")
                await bot.send_message(
                    chat_id=settings.admin_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    disable_web_page_preview=False,
                )
            except Exception as e:
                logger.error(f"Telegram send error: {e}")
                continue

            await _mark_published(item, category)

            async with async_session() as session:
                session.add(
                    AlertHistory(
                        user_id=settings.admin_id,
                        alert_type="news_intel",
                        asset_tags=",".join(assets),
                        title=(item.title or "")[:500],
                        body=text[:4000],
                        importance=importance.lower(),
                        raw_data={
                            "link": item.link,
                            "source": item.source,
                            "category": category,
                            "news_id": item.id,
                        },
                    )
                )
                await session.commit()

            published += 1
            logger.info(f"Published [{importance}] {item.title[:60]}")
            if published >= max_publish:
                break
        except Exception as e:
            logger.error(f"Publish pipeline error: {e}")

    return published


async def get_category_news(category: str, limit: int = 5) -> list:
    raw_list = collect_from_rss(max_per_feed=12)
    raw_list.sort(key=_sort_key, reverse=True)
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
