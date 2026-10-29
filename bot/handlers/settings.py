from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from bot.config import get_settings
from bot.keyboards.main_kb import main_reply_kb, settings_inline_kb
from bot.models.db import UserSettings, async_session
from bot.utils.i18n import t

router = Router(name="settings")
settings = get_settings()


@router.message(F.text.func(lambda t: t and ("настройки" in t.lower() or "settings" in t.lower() or "⚙️" in t)))
async def open_settings(message: Message):
    if message.from_user.id != settings.admin_id:
        return

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        lang = user.language
        only_high = user.only_high_impact

    await message.answer(
        f"⚙️ <b>{t('settings', lang)}</b>\n\n"
        f"Язык: {'🇷🇺 Русский' if lang == 'ru' else '🇬🇧 English'}\n"
        f"Только High Impact: {'Да' if only_high else 'Нет'}\n"
        f"Часовой пояс: {user.timezone}",
        reply_markup=settings_inline_kb(lang, only_high),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("settings:"))
async def settings_callback(callback: CallbackQuery):
    if callback.from_user.id != settings.admin_id:
        await callback.answer()
        return

    action = callback.data.split(":")[1]

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == callback.from_user.id)
        )
        user = result.scalar_one()

        if action == "toggle_high":
            user.only_high_impact = not user.only_high_impact
            await session.commit()
            await callback.answer("Updated")
            await callback.message.edit_reply_markup(
                reply_markup=settings_inline_kb(user.language, user.only_high_impact)
            )

        elif action == "toggle_lang":
            user.language = "en" if user.language == "ru" else "ru"
            await session.commit()
            await callback.answer(t("lang_switched", user.language))
            await callback.message.edit_text(
                f"⚙️ <b>{t('settings', user.language)}</b>\n\n"
                f"Язык: {'🇷🇺 Русский' if user.language == 'ru' else '🇬🇧 English'}\n"
                f"Только High Impact: {'Да' if user.only_high_impact else 'Нет'}\n"
                f"Часовой пояс: {user.timezone}",
                reply_markup=settings_inline_kb(user.language, user.only_high_impact),
                parse_mode="HTML",
            )
            # Also update reply keyboard
            await callback.message.answer(
                t("lang_switched", user.language),
                reply_markup=main_reply_kb(user.language, user.quiet_mode),
            )

        elif action == "back":
            await callback.message.delete()
            await callback.answer()

        else:
            await callback.answer()
