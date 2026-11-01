"""Macro Alert backend API — shared news, calendar, settings for Mini App.
Run: uvicorn api.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.auth import AuthError, TelegramUser, verify_init_data
from bot.config import get_settings, ASSETS
from bot.models.db import UserSettings, AnalyzedNews, async_session, init_db
from bot.services.calendar_service import fetch_calendar_raw
from bot.services.news_intelligence.categories import CATEGORIES
from bot.services.news_intelligence.publisher import (
    list_analyzed_news,
    ingest_and_cache,
    get_cached_analysis,
)

settings = get_settings()
app = FastAPI(title="Macro Alert API", version="1.0.0")

# CORS allowlist — set CORS_ORIGINS env comma-separated; default permissive for Mini App
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "PATCH", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Simple in-memory rate limit: user_id -> timestamps
_rate: Dict[int, List[float]] = defaultdict(list)
RATE_LIMIT = 60  # requests per minute


def _rate_check(uid: int) -> None:
    now = time.time()
    window = [t for t in _rate[uid] if now - t < 60]
    if len(window) >= RATE_LIMIT:
        raise HTTPException(429, "Rate limit exceeded")
    window.append(now)
    _rate[uid] = window


async def require_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    authorization: Optional[str] = Header(None),
) -> TelegramUser:
    raw = x_telegram_init_data
    if not raw and authorization and authorization.lower().startswith("tma "):
        raw = authorization[4:].strip()
    if not raw:
        raise HTTPException(401, "Missing Telegram initData")
    try:
        user = verify_init_data(raw)
    except AuthError as e:
        raise HTTPException(e.status_code, e.message)
    _rate_check(user.id)
    return user


class SettingsPatch(BaseModel):
    language: Optional[str] = Field(None, max_length=5)
    timezone: Optional[str] = Field(None, max_length=64)
    subscribed_assets: Optional[Dict[str, bool]] = None
    only_high_impact: Optional[bool] = None
    quiet_mode: Optional[bool] = None
    notifications_enabled: Optional[bool] = None


@app.on_event("startup")
async def _startup():
    await init_db()


@app.get("/api/health")
async def health():
    return {"ok": True, "service": "macro-alert"}


@app.get("/api/me")
async def me(user: TelegramUser = Depends(require_user)):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "language_code": user.language_code,
    }


@app.get("/api/me/settings")
async def get_settings_api(user: TelegramUser = Depends(require_user)):
    async with async_session() as session:
        r = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        row = r.scalar_one_or_none()
        if not row:
            row = UserSettings(
                user_id=user.id,
                subscribed_assets={k: True for k in ASSETS.keys()},
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {
            "language": row.language,
            "timezone": row.timezone,
            "subscribed_assets": row.subscribed_assets or {},
            "only_high_impact": row.only_high_impact,
            "quiet_mode": row.quiet_mode,
            "notifications_enabled": getattr(row, "notifications_enabled", True),
        }


@app.patch("/api/me/settings")
async def patch_settings(body: SettingsPatch, user: TelegramUser = Depends(require_user)):
    async with async_session() as session:
        r = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        row = r.scalar_one_or_none()
        if not row:
            row = UserSettings(user_id=user.id, subscribed_assets={k: True for k in ASSETS.keys()})
            session.add(row)
        if body.language is not None:
            row.language = body.language[:5]
        if body.timezone is not None:
            row.timezone = body.timezone[:64]
        if body.subscribed_assets is not None:
            # only known asset keys
            clean = {k: bool(v) for k, v in body.subscribed_assets.items() if k in ASSETS}
            row.subscribed_assets = clean
        if body.only_high_impact is not None:
            row.only_high_impact = body.only_high_impact
        if body.quiet_mode is not None:
            row.quiet_mode = body.quiet_mode
        if body.notifications_enabled is not None:
            row.notifications_enabled = body.notifications_enabled
        await session.commit()
        return {"ok": True}


def _news_to_dict(row: AnalyzedNews) -> dict:
    return {
        "id": row.news_id,
        "title": row.title,
        "summary": row.summary,
        "source": row.source,
        "link": row.link,
        "image": row.image,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "category": row.category,
        "assets": row.assets or [],
        "importance": row.importance,
        "bias": row.bias,
        "confidence": row.confidence,
        "analysis_ru": row.analysis_ru,
        "impact": row.impact or {},
        "method": row.method,
        "analyzed_at": row.analyzed_at.isoformat() if row.analyzed_at else None,
    }


@app.get("/api/news")
async def api_news(
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    refresh: bool = Query(False),
    user: TelegramUser = Depends(require_user),
):
    if refresh:
        try:
            await ingest_and_cache(limit=15)
        except Exception:
            pass
    rows = await list_analyzed_news(category, limit=limit)
    return {"items": [_news_to_dict(r) for r in rows], "count": len(rows)}


@app.get("/api/news/categories")
async def api_categories(user: TelegramUser = Depends(require_user)):
    return {
        "categories": [
            {
                "id": k,
                "emoji": v.get("emoji"),
                "name_ru": v.get("name_ru"),
                "name_en": v.get("name_en"),
            }
            for k, v in CATEGORIES.items()
        ]
    }


@app.get("/api/news/{news_id}")
async def api_news_one(news_id: str, user: TelegramUser = Depends(require_user)):
    row = await get_cached_analysis(news_id)
    if not row:
        raise HTTPException(404, "News not found")
    return _news_to_dict(row)


@app.get("/api/calendar")
async def api_calendar(user: TelegramUser = Depends(require_user)):
    raw = await fetch_calendar_raw()
    items = []
    for e in raw[:150]:
        items.append(
            {
                "title": e.get("name") or e.get("title") or "",
                "currency": e.get("currency") or e.get("country") or "",
                "impact": e.get("impact") or "Low",
                "date": e.get("date") or "",
                "forecast": e.get("forecast") or e.get("estimate") or "",
                "previous": e.get("previous") or "",
                "actual": e.get("actual") or "",
                "provider": e.get("_provider") or "unknown",
            }
        )
    return {"items": items, "count": len(items)}


@app.get("/api/market/status")
async def market_status(user: TelegramUser = Depends(require_user)):
    return {
        "assets": [
            {
                "key": k,
                "name": v.get("name_en"),
                "status": "live" if k in ("btc", "eth") else "limited",
                "source": "Binance" if k in ("btc", "eth") else (
                    "FX spot" if k in ("eurusd", "gbpusd", "usdjpy") else "unavailable"
                ),
            }
            for k, v in ASSETS.items()
        ]
    }
