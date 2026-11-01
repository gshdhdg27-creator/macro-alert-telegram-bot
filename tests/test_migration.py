"""SQLite migration: add notifications_enabled without losing users."""
import asyncio
import os
import tempfile

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_notifications_enabled_migration(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"

    try:
        # 1) Create OLD schema without notifications_enabled
        eng = create_async_engine(url)
        async with eng.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE user_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE,
                        language VARCHAR(5) DEFAULT 'ru',
                        timezone VARCHAR(64) DEFAULT 'Europe/Moscow',
                        subscribed_assets JSON,
                        only_high_impact BOOLEAN DEFAULT 0,
                        quiet_mode BOOLEAN DEFAULT 0
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO user_settings (user_id, language, quiet_mode) "
                    "VALUES (7257793582, 'ru', 0)"
                )
            )
        await eng.dispose()

        # 2) Point app settings at this DB and run migrate
        from bot import config as cfg

        class S:
            database_url = url
            bot_token = "x"
            admin_id = 1

        monkeypatch.setattr(cfg, "get_settings", lambda: S())

        # re-import engine binding is sticky — use migrate logic directly
        from bot.models import db as dbmod

        # rebuild module engine for this URL
        dbmod.engine = create_async_engine(url)
        dbmod.async_session = __import__("sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]).async_sessionmaker(
            dbmod.engine, class_=__import__("sqlalchemy.ext.asyncio", fromlist=["AsyncSession"]).AsyncSession,
            expire_on_commit=False,
        )

        await dbmod.migrate_schema()

        # 3) Verify column + user preserved
        async with dbmod.engine.begin() as conn:
            cols = (await conn.execute(text("PRAGMA table_info(user_settings)"))).fetchall()
            names = {c[1] for c in cols}
            assert "notifications_enabled" in names

            row = (
                await conn.execute(
                    text("SELECT user_id, notifications_enabled FROM user_settings WHERE user_id=7257793582")
                )
            ).fetchone()
            assert row is not None
            assert row[0] == 7257793582
            assert row[1] in (1, True)

        # 4) ORM query works
        from sqlalchemy import select
        from bot.models.db import UserSettings

        async with dbmod.async_session() as session:
            r = await session.execute(select(UserSettings).where(UserSettings.user_id == 7257793582))
            u = r.scalar_one()
            assert u.user_id == 7257793582
            assert u.notifications_enabled is True

        # 5) Idempotent second run
        await dbmod.migrate_schema()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
