"""Publish analyzed news — subscription-aware, DB dedupe, analysis cache."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot
from loguru import logger
from sqlalchemy import select, desc

from bot.config import get_settings
from bot.models.db import (
    UserSettings,
    AlertHistory,
    PublishedNews,
    AnalyzedNews,
    async_session,
)
from bot.services.alert_service import _tags_match_subscriptions
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


async def _save_analysis(item: RawNews, category: str, assets: list, analysis: Dict[str, Any]) -> None:
    async with async_session() as session:
        try:
            existing = await session.execute(
                select(AnalyzedNews).where(AnalyzedNews.news_id == item.id).limit(1)
            )
            row = existing.scalar_one_or_none()
            payload = dict(
                title=(item.title or "")[:500],
                summary=(item.summary or "")[:4000],
                source=item.source,
                link=item.link,
                image=getattr(item, "image", None),
                published_at=item.published,
                category=category,
                assets=assets,
                importance=analysis.get("importance"),
                bias=analysis.get("bias"),
                confidence=analysis.get("confidence"),
                analysis_ru=analysis.get("analysis_ru"),
                impact=analysis.get("impact"),
                method=analysis.get("method"),
                analyzed_at=datetime.now(timezone.utc),
            )
            if row:
                for k, v in payload.items():
                    setattr(row, k, v)
            else:
                session.add(AnalyzedNews(news_id=item.id, **payload))
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning(f"analysis cache save failed: {e}")


async def get_cached_analysis(news_id: str) -> Optional[AnalyzedNews]:
    async with async_session() as session:
        r = await session.execute(
            select(AnalyzedNews).where(AnalyzedNews.news_id == news_id).limit(1)
        )
        return r.scalar_one_or_none()


async def list_analyzed_news(
    category: Optional[str] = None,
    limit: int = 30,
) -> List[AnalyzedNews]:
    async with async_session() as session:
        q = select(AnalyzedNews).order_by(desc(AnalyzedNews.created_at)).limit(min(limit, 100))
        if category and category != "all":
            q = select(AnalyzedNews).where(AnalyzedNews.category == category).order_by(
                desc(AnalyzedNews.created_at)
            ).limit(min(limit, 100))
        r = await session.execute(q)
        return list(r.scalars().all())


async def _user_allows_publish(assets: list, importance: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == settings.admin_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return True  # first-run: allow until settings exist
        if getattr(user, "notifications_enabled", True) is False:
            return False
        if user.quiet_mode:
            return False
        if user.only_high_impact and importance not in ("HIGH", "CRITICAL"):
            return False
        tags = ",".join(assets or [])
        # Empty subscriptions dict or all-true → treat as subscribed to all
        subs = user.subscribed_assets or {}
        if not subs:
            return True
        if any(subs.values()) is False and not any(subs.values()):
            # all explicitly false
            return False
        if not any(subs.values()):
            return False
        # Global macro / no asset tags → allow if any subscription exists
        if not tags:
            return True
        return _tags_match_subscriptions(tags, subs)


async def process_and_publish(bot: Bot, max_publish: int = 2) -> int:
    raw_list = collect_from_rss()
    published = 0
    raw_list.sort(key=_sort_key, reverse=True)

    for item in raw_list:
        try:
            if await _already_published(item.id):
                continue

            category, assets = classify(item)
            cached = await get_cached_analysis(item.id)
            if cached and cached.analysis_ru:
                analysis = {
                    "category": cached.category or category,
                    "assets": cached.assets or assets,
                    "importance": cached.importance or "MEDIUM",
                    "bias": cached.bias or "NEUTRAL",
                    "confidence": cached.confidence or "LOW",
                    "analysis_ru": cached.analysis_ru,
                    "impact": cached.impact or {},
                    "method": cached.method or "rule-based",
                }
            else:
                analysis = await analyze(item, category, assets)
                await _save_analysis(item, category, assets, analysis)

            importance = analysis.get("importance", "MEDIUM")
            if importance not in ("MEDIUM", "HIGH", "CRITICAL"):
                await _mark_published(item, category)
                continue

            if not await _user_allows_publish(assets, importance):
                logger.info(f"Skip publish (prefs/subscriptions): {item.title[:60]}")
                await _mark_published(item, category)
                continue

            text = format_news_message(
                item,
                analysis,
                pub_type="BREAKING NEWS" if importance == "CRITICAL" else "MARKET NEWS",
            )
            kb = news_inline_kb(item, category)

            try:
                if item.image and str(item.image).startswith("https://"):
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


async def ingest_and_cache(limit: int = 20) -> int:
    """Collect + analyze + store without Telegram send (for API refresh)."""
    raw_list = collect_from_rss()
    raw_list.sort(key=_sort_key, reverse=True)
    n = 0
    for item in raw_list[:limit]:
        try:
            if await get_cached_analysis(item.id):
                continue
            category, assets = classify(item)
            analysis = await analyze(item, category, assets)
            await _save_analysis(item, category, assets, analysis)
            n += 1
        except Exception as e:
            logger.warning(f"ingest: {e}")
    return n


async def get_category_news(category: str, limit: int = 5) -> list:
    cached = await list_analyzed_news(category if category != "all" else None, limit=limit)
    if cached:
        out = []
        for row in cached:
            item = RawNews(
                id=row.news_id,
                title=row.title,
                summary=row.summary or "",
                link=row.link or "",
                source=row.source or "",
                published=row.published_at,
            )
            analysis = {
                "category": row.category,
                "assets": row.assets or [],
                "importance": row.importance,
                "bias": row.bias,
                "confidence": row.confidence,
                "analysis_ru": row.analysis_ru,
                "impact": row.impact or {},
                "method": row.method,
            }
            out.append((item, analysis))
        return out

    raw_list = collect_from_rss(max_per_feed=12)
    raw_list.sort(key=_sort_key, reverse=True)
    out = []
    for item in raw_list:
        cat, assets = classify(item)
        if category != "all" and cat != category:
            from bot.services.news_intelligence.categories import CATEGORIES

            text = f"{item.title} {item.summary}".lower()
            kws = CATEGORIES.get(category, {}).get("keywords") or []
            if not any(k in text for k in kws):
                continue
        analysis = await analyze(item, category if category != "all" else cat, assets)
        await _save_analysis(item, cat, assets, analysis)
        out.append((item, analysis))
        if len(out) >= limit:
            break
    return out
