"""SQLite migration: add notifications_enabled without losing users."""
import os
import tempfile

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_notifications_enabled_migration(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"

    try:
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

        from bot import config as cfg

        class S:
            database_url = url
            bot_token = "x"
            admin_id = 1

        monkeypatch.setattr(cfg, "get_settings", lambda: S())

        from bot.models import db as dbmod

        dbmod.engine = create_async_engine(url)
        dbmod.async_session = async_sessionmaker(
            dbmod.engine, class_=AsyncSession, expire_on_commit=False
        )

        await dbmod.migrate_schema()

        async with dbmod.engine.begin() as conn:
            cols = (await conn.execute(text("PRAGMA table_info(user_settings)"))).fetchall()
            names = {c[1] for c in cols}
            assert "notifications_enabled" in names

            row = (
                await conn.execute(
                    text(
                        "SELECT user_id, notifications_enabled FROM user_settings "
                        "WHERE user_id=7257793582"
                    )
                )
            ).fetchone()
            assert row is not None
            assert row[0] == 7257793582
            assert int(row[1]) == 1

        from bot.models.db import UserSettings

        async with dbmod.async_session() as session:
            r = await session.execute(
                select(UserSettings).where(UserSettings.user_id == 7257793582)
            )
            u = r.scalar_one()
            assert u.user_id == 7257793582
            assert bool(u.notifications_enabled) is True

        await dbmod.migrate_schema()  # idempotent
        await dbmod.engine.dispose()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
