from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy import select

from bot.config import get_settings
from bot.keyboards.main_kb import main_reply_kb
from bot.models.db import UserSettings, async_session
from bot.utils.i18n import t

router = Router(name="start")
settings = get_settings()


@router.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id != settings.admin_id:
        await message.answer("⛔ This bot is private.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = UserSettings(
                user_id=message.from_user.id,
                language="ru",
                timezone=settings.default_timezone,
                subscribed_assets={k: True for k in [
                    "xauusd", "nasdaq", "sp500", "btc", "eth", "dxy",
                    "oil", "eurusd", "gbpusd", "usdjpy", "agro", "tesla", "ai_tech"
                ]},
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        lang = user.language
        quiet = user.quiet_mode

    await message.answer(
        t("welcome", lang),
        reply_markup=main_reply_kb(lang=lang, quiet=quiet),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id != settings.admin_id:
        return
    await message.answer(
        "📚 Команды:\n"
        "/start — перезапуск\n"
        "/help — помощь\n"
        "/status — статус бота\n\n"
        "Используй кнопки меню для навигации."
    )
