from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from bot.config import get_settings
from bot.keyboards.main_kb import calendar_period_kb, main_reply_kb
from bot.models.db import UserSettings, async_session
from bot.services.calendar_service import get_calendar_events
from bot.utils.i18n import t

router = Router(name="calendar")
settings = get_settings()


@router.message(F.text.func(lambda t: t and ("календар" in t.lower() or "calendar" in t.lower() or "📅" in t)))
async def open_calendar(message: Message):
    if message.from_user.id != settings.admin_id:
        return

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ru"

    await message.answer(
        f"📅 <b>{t('calendar', lang)}</b>\n\nВыбери период:",
        reply_markup=calendar_period_kb(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cal:"))
async def calendar_callback(callback: CallbackQuery):
    if callback.from_user.id != settings.admin_id:
        await callback.answer()
        return

    period = callback.data.split(":")[1]

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == callback.from_user.id)
        )
        user = result.scalar_one()
        lang = user.language
        tz = user.timezone

    if period == "back":
        await callback.message.delete()
        await callback.answer()
        return

    await callback.answer()
    await callback.message.edit_text(t("loading", lang))

    try:
        events = await get_calendar_events(period=period, timezone=tz, lang=lang)
        if not events:
            text = t("no_events", lang)
        else:
            text = f"📅 <b>{t('calendar', lang)} — {period}</b>\n\n" + "\n\n".join(events)

        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(f"{t('error', lang)}\n<code>{e}</code>", parse_mode="HTML")
