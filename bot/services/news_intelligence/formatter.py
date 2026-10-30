"""Telegram HTML message formatter — Macro Alert visual style."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.services.news_intelligence.categories import CATEGORIES
from bot.services.news_intelligence.collector import RawNews

BIAS_EMOJI = {
    "BULLISH": "🟢",
    "BEARISH": "🔴",
    "NEUTRAL": "⚪",
    "UNCERTAIN": "🟡",
}

IMP_EMOJI = {
    "CRITICAL": "🚨",
    "HIGH": "🔴",
    "MEDIUM": "🟠",
    "LOW": "🟡",
}


def format_news_message(
    item: RawNews,
    analysis: Dict[str, Any],
    pub_type: str = "NEWS",
) -> str:
    cat_id = analysis.get("category", "economic")
    cat = CATEGORIES.get(cat_id, {})
    emoji = cat.get("emoji", "📰")
    cat_name = cat.get("name_ru", cat_id.upper())
    bias = analysis.get("bias", "NEUTRAL")
    importance = analysis.get("importance", "MEDIUM")
    impact = analysis.get("impact") or {}
    assets = analysis.get("assets") or []

    if item.published:
        when = item.published.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    else:
        when = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    impact_lines = []
    for a, d in impact.items():
        impact_lines.append(f"  • {a}: {BIAS_EMOJI.get(d, '⚪')} {d}")
    impact_block = "\n".join(impact_lines) if impact_lines else "  • MARKET: " + bias

    assets_str = ", ".join(assets) if assets else "—"
    summary = item.summary[:500] + ("…" if len(item.summary) > 500 else "") if item.summary else item.title

    # FIX: Unicode dash must be a string literal, not a bare identifier
    sep = "━" * 18

    text = (
        f"{IMP_EMOJI.get(importance, '🟠')} <b>{pub_type}</b> | {emoji} <b>{cat_name}</b>\n"
        f"{sep}\n\n"
        f"<b>{item.title}</b>\n"
        f"<i>{when}</i>\n\n"
        f"<b>ЧТО ПРОИЗОШЛО?</b>\n"
        f"{summary}\n\n"
        f"<b>ЗАТРОНУТЫЕ АКТИВЫ:</b>\n{assets_str}\n\n"
        f"<b>ВЛИЯНИЕ НА РЫНОК:</b>\n{impact_block}\n\n"
        f"<b>AI MARKET ANALYSIS:</b>\n"
        f"{analysis.get('analysis_ru', '—')}\n\n"
        f"<b>ВАЖНОСТЬ:</b> {importance}\n"
        f"<b>ИСТОЧНИК:</b> {item.source}"
    )
    if item.link:
        text += f'\n<a href="{item.link}">Открыть первоисточник</a>'
    return text


def news_inline_kb(item: RawNews, category: str) -> InlineKeyboardMarkup:
    rows = []
    if item.link:
        rows.append([InlineKeyboardButton(text="🌐 Источник", url=item.link)])
    rows.append([
        InlineKeyboardButton(text="📰 Все новости", callback_data="news:menu"),
        InlineKeyboardButton(
            text=f"{CATEGORIES.get(category, {}).get('emoji', '📰')} Категория",
            callback_data=f"news:cat:{category}",
        ),
    ])
    rows.append([
        InlineKeyboardButton(text="📈 Trade", callback_data="news:trade"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    from bot.services.news_intelligence.categories import PRIMARY_CATS, CATEGORIES

    rows = []
    row = []
    for key in PRIMARY_CATS:
        c = CATEGORIES[key]
        name = c["name_ru"] if lang == "ru" else c["name_en"]
        row.append(InlineKeyboardButton(
            text=f"{c['emoji']} {name}",
            callback_data=f"news:cat:{key}",
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔥 Breaking / Latest", callback_data="news:latest")])
    rows.append([InlineKeyboardButton(text="📅 Calendar FF", callback_data="open_calendar")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
