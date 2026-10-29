from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select
import os

from bot.config import get_settings, ASSETS
from bot.keyboards.main_kb import main_reply_kb
from bot.models.db import UserSettings, async_session
from bot.utils.i18n import t

router = Router(name="start")
settings = get_settings()

# Set in .env: MINIAPP_URL=https://your-deployment.vercel.app
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://macro-alert-telegram-bot.vercel.app")


def get_start_inline_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Trade", web_app=WebAppInfo(url=MINIAPP_URL))],
        [
            InlineKeyboardButton(
                text="📅 Календарь" if lang == "ru" else "📅 Calendar",
                callback_data="open_calendar",
            ),
            InlineKeyboardButton(
                text="⚙️ Настройки" if lang == "ru" else "⚙️ Settings",
                callback_data="open_settings",
            ),
        ],
    ])


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
                subscribed_assets={k: True for k in ASSETS.keys()},
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        lang = user.language
        quiet = user.quiet_mode

    welcome_text = (
        "📊 <b>Macro Alert</b>\n\n"
        "Персональный терминал макроэкономики и активов.\n\n"
        "• Живые графики (свечи / линия)\n"
        "• Экономический календарь (ФРС, CPI, NFP…)\n"
        "• Умные алерты по 13 активам\n"
        "• AI-фильтрация новостей\n\n"
        "Нажми <b>Trade</b>, чтобы открыть терминал."
        if lang == "ru"
        else
        "📊 <b>Macro Alert</b>\n\n"
        "Personal macro & assets terminal.\n\n"
        "• Live charts (candles / line)\n"
        "• Economic calendar (Fed, CPI, NFP…)\n"
        "• Smart alerts for 13 assets\n"
        "• AI news filtering\n\n"
        "Tap <b>Trade</b> to open the terminal."
    )

    await message.answer(
        welcome_text,
        reply_markup=get_start_inline_kb(lang),
        parse_mode="HTML",
    )
    await message.answer(
        "Выбери раздел ↓" if lang == "ru" else "Choose section ↓",
        reply_markup=main_reply_kb(lang=lang, quiet=quiet),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id != settings.admin_id:
        return
    await message.answer(
        "📚 /start — перезапуск\n"
        "/help — помощь\n\n"
        "Используй кнопку <b>Trade</b> или меню."
    )
