"""API endpoint auth and settings persistence tests."""
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import pytest
from httpx import ASGITransport, AsyncClient

BOT_TOKEN = "123456:API_TEST_TOKEN"
ADMIN_ID = 42


def official_sign(fields: dict, bot_token: str = BOT_TOKEN) -> str:
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(bot_token.encode("utf-8"), b"WebAppData", hashlib.sha256).digest()
    return hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()


def make_init_data(user_id: int = ADMIN_ID) -> str:
    fields = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": user_id, "username": "admin"}, separators=(",", ":")),
        "query_id": "AAE",
    }
    fields["hash"] = official_sign(fields)
    return urlencode(fields)


@pytest.fixture
async def client(monkeypatch, tmp_path):
    db_path = tmp_path / "api_test.db"
    url = f"sqlite+aiosqlite:///{db_path}"

    os.environ["BOT_TOKEN"] = BOT_TOKEN
    os.environ["ADMIN_ID"] = str(ADMIN_ID)
    os.environ["DATABASE_URL"] = url
    os.environ["CORS_ORIGINS"] = "http://testserver,http://localhost:3000"

    from bot.config import get_settings

    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()

    import bot.config as cfg

    class S:
        bot_token = BOT_TOKEN
        admin_id = ADMIN_ID
        database_url = url
        openai_api_key = ""
        openai_model = "gpt-4o-mini"
        fmp_api_key = ""

    monkeypatch.setattr(cfg, "get_settings", lambda: S())

    import api.auth as auth_mod

    monkeypatch.setattr(auth_mod, "get_settings", lambda: S())

    from bot.models import db as dbmod
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    dbmod.engine = create_async_engine(url)
    dbmod.async_session = async_sessionmaker(dbmod.engine, class_=AsyncSession, expire_on_commit=False)
    await dbmod.init_db()

    import api.app as app_mod
    from bot.services.news_intelligence import publisher as pub_mod
    from bot.services import calendar_service as cal_mod

    monkeypatch.setattr(app_mod, "settings", S())
    monkeypatch.setattr(app_mod, "async_session", dbmod.async_session)
    monkeypatch.setattr(pub_mod, "async_session", dbmod.async_session)
    monkeypatch.setattr(cal_mod, "async_session", dbmod.async_session)

    async def _empty_cal():
        return []

    async def _empty_news(*a, **k):
        return []

    monkeypatch.setattr(app_mod, "fetch_calendar_raw", _empty_cal)
    monkeypatch.setattr(app_mod, "list_analyzed_news", _empty_news)

    transport = ASGITransport(app=app_mod.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    await dbmod.engine.dispose()
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_me_missing_auth(client):
    r = await client.get("/api/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_auth(client):
    r = await client.get("/api/me", headers={"X-Telegram-Init-Data": "hash=00&auth_date=1"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_valid_admin(client):
    init = make_init_data(ADMIN_ID)
    r = await client.get("/api/me", headers={"X-Telegram-Init-Data": init})
    assert r.status_code == 200
    assert r.json()["id"] == ADMIN_ID


@pytest.mark.asyncio
async def test_settings_get_patch_persist(client):
    init = make_init_data(ADMIN_ID)
    h = {"X-Telegram-Init-Data": init}

    r = await client.get("/api/me/settings", headers=h)
    assert r.status_code == 200
    assert "subscribed_assets" in r.json()

    r2 = await client.patch(
        "/api/me/settings",
        headers=h,
        json={
            "quiet_mode": True,
            "notifications_enabled": False,
            "subscribed_assets": {"btc": True, "eth": False, "not_a_real_asset": True},
        },
    )
    assert r2.status_code == 200

    r3 = await client.get("/api/me/settings", headers=h)
    assert r3.status_code == 200
    data = r3.json()
    assert data["quiet_mode"] is True
    assert data["notifications_enabled"] is False
    assert data["subscribed_assets"].get("btc") is True
    assert data["subscribed_assets"].get("eth") is False
    assert "not_a_real_asset" not in data["subscribed_assets"]


@pytest.mark.asyncio
async def test_news_and_calendar_auth(client):
    init = make_init_data(ADMIN_ID)
    h = {"X-Telegram-Init-Data": init}
    for path in ("/api/news", "/api/news/categories", "/api/calendar", "/api/market/status"):
        r = await client.get(path, headers=h)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"
        r401 = await client.get(path)
        assert r401.status_code == 401, path
