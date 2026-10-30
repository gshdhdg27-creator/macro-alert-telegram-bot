"""Telegram HTML message formatter — Macro Alert visual style. Escapes all dynamic content."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

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


def _e(s: Any) -> str:
    """Escape for Telegram HTML."""
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def _safe_https(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        p = urlparse(url.strip())
        if p.scheme == "https" and p.netloc:
            return url.strip()
    except Exception:
        pass
    return None


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
    confidence = analysis.get("confidence", "LOW")
    method = analysis.get("method", "rule-based")
    impact = analysis.get("impact") or {}
    assets = analysis.get("assets") or []

    if item.published:
        when = item.published.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    else:
        when = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    impact_lines = []
    for a, d in impact.items():
        impact_lines.append(f"  • {_e(a)}: {BIAS_EMOJI.get(str(d), '⚪')} {_e(d)}")
    impact_block = "\n".join(impact_lines) if impact_lines else f"  • MARKET: {_e(bias)}"

    assets_str = ", ".join(_e(a) for a in assets) if assets else "—"
    summary_raw = item.summary if item.summary else item.title
    summary = _e(summary_raw[:800] + ("…" if len(summary_raw) > 800 else ""))

    sep = "━" * 18
    analysis_text = _e(analysis.get("analysis_ru") or "—")

    text = (
        f"{IMP_EMOJI.get(importance, '🟠')} <b>{_e(pub_type)}</b> | {emoji} <b>{_e(cat_name)}</b>\n"
        f"{sep}\n\n"
        f"<b>{_e(item.title)}</b>\n"
        f"<i>{_e(when)}</i>\n\n"
        f"<b>ЧТО ПРОИЗОШЛО?</b>\n"
        f"{summary}\n\n"
        f"<b>ЗАТРОНУТЫЕ АКТИВЫ:</b>\n{assets_str}\n\n"
        f"<b>ВЛИЯНИЕ НА РЫНОК:</b>\n{impact_block}\n\n"
        f"<b>АНАЛИЗ ({_e(method)}):</b>\n"
        f"{analysis_text}\n\n"
        f"<b>ВАЖНОСТЬ:</b> {_e(importance)}\n"
        f"<b>CONFIDENCE:</b> {_e(confidence)}\n"
        f"<b>ИСТОЧНИК:</b> {_e(item.source)}"
    )
    safe_link = _safe_https(item.link)
    if safe_link:
        text += f'\n<a href="{_e(safe_link)}">Открыть первоисточник</a>'
    return text


def news_inline_kb(item: RawNews, category: str) -> InlineKeyboardMarkup:
    rows = []
    safe_link = _safe_https(item.link)
    if safe_link:
        rows.append([InlineKeyboardButton(text="🌐 Источник", url=safe_link)])
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
