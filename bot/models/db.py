from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot.config import get_settings


class Base(DeclarativeBase):
    pass


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    language: Mapped[str] = mapped_column(String(5), default="ru")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    subscribed_assets: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    only_high_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    alert_type: Mapped[str] = mapped_column(String(32))
    asset_tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(String(16), default="medium")
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class PublishedNews(Base):
    __tablename__ = "published_news"
    __table_args__ = (UniqueConstraint("news_id", name="uq_published_news_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class CalendarAlert(Base):
    __tablename__ = "calendar_alerts"
    __table_args__ = (UniqueConstraint("event_id", "alert_kind", name="uq_cal_event_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    alert_kind: Mapped[str] = mapped_column(String(32))
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyzedNews(Base):
    __tablename__ = "analyzed_news"
    __table_args__ = (UniqueConstraint("news_id", name="uq_analyzed_news_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    assets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    importance: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    bias: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    analysis_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _column_exists(conn, table: str, column: str) -> bool:
    # SQLite PRAGMA
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    rows = result.fetchall()
    cols = {r[1] for r in rows}  # name is index 1
    return column in cols


async def migrate_schema() -> None:
    """Idempotent schema upgrades without dropping data."""
    async with engine.begin() as conn:
        # Ensure base tables exist
        await conn.run_sync(Base.metadata.create_all)

        # user_settings.notifications_enabled
        try:
            # Only apply PRAGMA path for SQLite
            url = str(engine.url)
            if "sqlite" in url:
                exists = await _column_exists(conn, "user_settings", "notifications_enabled")
                if not exists:
                    logger.info("Migrating: ADD user_settings.notifications_enabled DEFAULT 1")
                    await conn.execute(
                        text(
                            "ALTER TABLE user_settings "
                            "ADD COLUMN notifications_enabled BOOLEAN DEFAULT 1 NOT NULL"
                        )
                    )
                    # Explicitly set TRUE for any existing NULL rows (safety)
                    await conn.execute(
                        text(
                            "UPDATE user_settings SET notifications_enabled = 1 "
                            "WHERE notifications_enabled IS NULL"
                        )
                    )
                    logger.info("Migration complete: notifications_enabled")
        except Exception as e:
            logger.error(f"migrate_schema error: {e}")
            raise


async def init_db() -> None:
    await migrate_schema()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
