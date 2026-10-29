from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from bot.config import ASSETS, get_settings
from bot.keyboards.main_kb import main_reply_kb, asset_subscribe_kb
from bot.models.db import UserSettings, async_session
from bot.utils.i18n import t

router = Router(name="menu")
settings = get_settings()


def _match_asset(text: str) -> str | None:
    text_lower = text.lower()
    for key, asset in ASSETS.items():
        if asset["emoji"] in text or asset["name_ru"].lower() in text_lower or asset["name_en"].lower() in text_lower:
            return key
    return None


@router.message(F.text)
async def handle_menu_text(message: Message):
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
        quiet = user.quiet_mode

    text = message.text or ""

    # Quiet mode toggle
    if t("quiet_on", lang) in text or t("quiet_off", lang) in text or "тихий" in text.lower() or "quiet" in text.lower():
        async with async_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == message.from_user.id)
            )
            user = result.scalar_one()
            user.quiet_mode = not user.quiet_mode
            await session.commit()
            new_quiet = user.quiet_mode

        msg = t("quiet_enabled" if new_quiet else "quiet_disabled", lang)
        await message.answer(msg, reply_markup=main_reply_kb(lang=lang, quiet=new_quiet))
        return

    # Asset selection
    asset_key = _match_asset(text)
    if asset_key:
        asset = ASSETS[asset_key]
        name = asset["name_ru"] if lang == "ru" else asset["name_en"]
        subscribed = bool((user.subscribed_assets or {}).get(asset_key, False))

        info = (
            f"{asset['emoji']} <b>{name}</b>\n\n"
            f"Теги: {', '.join('#' + t for t in asset['tags'][:5])}\n\n"
            f"Статус подписки: {'✅ Включена' if subscribed else '❌ Выключена'}"
        )
        await message.answer(
            info,
            reply_markup=asset_subscribe_kb(asset_key, subscribed, lang),
            parse_mode="HTML",
        )
        return

    # Fallback — show main menu
    if text in [t("main_menu", lang), "меню", "menu"]:
        await message.answer(t("main_menu", lang), reply_markup=main_reply_kb(lang, quiet))
