from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.config import ASSETS
from bot.utils.i18n import t


def main_reply_kb(lang: str = "ru", quiet: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    # Assets row by row (3 per row)
    asset_keys = list(ASSETS.keys())
    for i in range(0, len(asset_keys), 3):
        row = []
        for key in asset_keys[i : i + 3]:
            asset = ASSETS[key]
            name = asset["name_ru"] if lang == "ru" else asset["name_en"]
            row.append(KeyboardButton(text=f"{asset['emoji']} {name}"))
        builder.row(*row)

    # System buttons
    builder.row(
        KeyboardButton(text=t("calendar", lang)),
        KeyboardButton(text=t("settings", lang)),
    )
    builder.row(
        KeyboardButton(text=t("history", lang)),
        KeyboardButton(text=t("quiet_on" if not quiet else "quiet_off", lang)),
    )

    return builder.as_markup(resize_keyboard=True)


def settings_inline_kb(lang: str = "ru", only_high: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=f"{'✅' if only_high else '⬜️'} {t('only_high', lang)}",
            callback_data="settings:toggle_high",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🇷🇺 Русский" if lang == "en" else "🇬🇧 English",
            callback_data="settings:toggle_lang",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🕒 {t('timezone', lang)}",
            callback_data="settings:timezone",
        )
    )
    builder.row(
        InlineKeyboardButton(text=t("back", lang), callback_data="settings:back")
    )

    return builder.as_markup()


def calendar_period_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("today", lang), callback_data="cal:today"),
        InlineKeyboardButton(text=t("tomorrow", lang), callback_data="cal:tomorrow"),
    )
    builder.row(
        InlineKeyboardButton(text=t("week", lang), callback_data="cal:week"),
    )
    builder.row(
        InlineKeyboardButton(text=t("back", lang), callback_data="cal:back")
    )
    return builder.as_markup()


def asset_subscribe_kb(asset_key: str, subscribed: bool, lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    action = "unsub" if subscribed else "sub"
    text = t("unsubscribed" if subscribed else "subscribed", lang, asset=ASSETS[asset_key]["name_ru" if lang == "ru" else "name_en"])
    # simpler button text
    btn_text = "❌ Отписаться" if subscribed and lang == "ru" else "✅ Подписаться" if not subscribed and lang == "ru" else ("❌ Unsubscribe" if subscribed else "✅ Subscribe")
    builder.row(
        InlineKeyboardButton(text=btn_text, callback_data=f"asset:{action}:{asset_key}")
    )
    builder.row(
        InlineKeyboardButton(text=t("back", lang), callback_data="asset:back")
    )
    return builder.as_markup()
