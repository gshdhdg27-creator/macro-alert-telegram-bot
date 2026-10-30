"""Handlers for Trading AI News Intelligence menu & categories."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.config import get_settings
from bot.services.news_intelligence.categories import CATEGORIES, category_list_text
from bot.services.news_intelligence.formatter import categories_kb, format_news_message, news_inline_kb
from bot.services.news_intelligence.publisher import get_category_news

router = Router(name="news_agent")
settings = get_settings()


def _admin(uid: int) -> bool:
    return uid == settings.admin_id


@router.message(Command("news"))
@router.message(F.text.in_({"📰 Новости", "📰 News", "Новости AI", "AI News"}))
async def open_news_menu(message: Message):
    if not _admin(message.from_user.id):
        return
    text = (
        "📰 <b>Trading AI News Intelligence</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "Профессиональные финансовые новости с AI-анализом.\n"
        "Только проверенные источники. Без выдумок.\n\n"
        "<b>Категории:</b>\n"
        f"{category_list_text('ru')}\n\n"
        "Выберите категорию ↓"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=categories_kb("ru"))


@router.callback_query(F.data == "news:menu")
async def cb_news_menu(cq: CallbackQuery):
    if not _admin(cq.from_user.id):
        await cq.answer()
        return
    await cq.message.answer(
        "📰 <b>Trading AI News Intelligence</b>\n\nВыберите категорию ↓",
        parse_mode="HTML",
        reply_markup=categories_kb("ru"),
    )
    await cq.answer()


@router.callback_query(F.data == "news:latest")
async def cb_latest(cq: CallbackQuery):
    if not _admin(cq.from_user.id):
        await cq.answer()
        return
    await cq.answer("Загрузка…")
    items = await get_category_news("all", limit=3)
    if not items:
        await cq.message.answer("Сейчас нет свежих подтверждённых новостей.")
        return
    for item, analysis in items:
        text = format_news_message(item, analysis, pub_type="MARKET NEWS")
        await cq.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=news_inline_kb(item, analysis.get("category", "economic")),
            disable_web_page_preview=False,
        )


@router.callback_query(F.data.startswith("news:cat:"))
async def cb_category(cq: CallbackQuery):
    if not _admin(cq.from_user.id):
        await cq.answer()
        return
    cat = cq.data.split(":")[-1]
    meta = CATEGORIES.get(cat)
    if not meta:
        await cq.answer("Unknown")
        return
    await cq.answer(f"{meta['emoji']} {meta['name_ru']}")
    items = await get_category_news(cat, limit=3)
    if not items:
        await cq.message.answer(
            f"{meta['emoji']} <b>{meta['name_ru']}</b>\n\n"
            "Сейчас нет подтверждённых новостей по этой категории.\n"
            "Агент не публикует выдуманные события.",
            parse_mode="HTML",
            reply_markup=categories_kb("ru"),
        )
        return
    await cq.message.answer(
        f"{meta['emoji']} <b>{meta['name_ru']}</b> — свежая подборка",
        parse_mode="HTML",
    )
    for item, analysis in items:
        text = format_news_message(item, analysis, pub_type="MARKET NEWS")
        await cq.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=news_inline_kb(item, cat),
            disable_web_page_preview=False,
        )


@router.callback_query(F.data == "news:trade")
async def cb_trade(cq: CallbackQuery):
    await cq.answer("Открой Trade в /start")
