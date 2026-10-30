"""Market analysis — never invents prices/events. CRITICAL only for exceptional cases."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from loguru import logger

from bot.config import get_settings
from bot.services.news_intelligence.categories import CATEGORIES
from bot.services.news_intelligence.collector import RawNews

settings = get_settings()

ALLOWED_BIAS = {"BULLISH", "BEARISH", "NEUTRAL", "UNCERTAIN"}
ALLOWED_IMP = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
ALLOWED_CONF = {"LOW", "MEDIUM", "HIGH"}

BULLISH_HINTS = [
    "surge", "rally", "rise", "gain", "beat", "stronger", "growth", "approval",
    "inflow", "record high", "boost", "optimistic", "cut rates", "stimulus",
]
BEARISH_HINTS = [
    "fall", "drop", "plunge", "decline", "miss", "weaker", "recession", "sanction",
    "outflow", "hack", "ban", "hike rates", "inflation jump", "layoff", "crisis",
]


def _bias_from_text(text: str) -> str:
    t = text.lower()
    b = sum(1 for h in BULLISH_HINTS if h in t)
    r = sum(1 for h in BEARISH_HINTS if h in t)
    if b >= 2 and b > r:
        return "BULLISH"
    if r >= 2 and r > b:
        return "BEARISH"
    if b > 0 or r > 0:
        return "UNCERTAIN"
    return "NEUTRAL"


def _importance(text: str, category: str) -> str:
    """CRITICAL only for genuinely exceptional language — not every FOMC mention."""
    t = text.lower()
    critical_kw = [
        "emergency rate", "market crash", "sovereign default", "bank run",
        "nuclear", "declaration of war", "systemic failure",
    ]
    high_kw = [
        "rate decision", "fomc statement", "nfp ", "nonfarm payroll",
        "cpi ", "interest rate decision", "etf approved", "hack ",
    ]
    if any(k in t for k in critical_kw):
        return "CRITICAL"
    if any(k in t for k in high_kw) or category in ("central_banks",):
        return "HIGH"
    if category in ("economic", "geopolitics", "whales", "crypto"):
        return "MEDIUM"
    return "MEDIUM"


def _validate_analysis(data: dict, fallback: dict) -> dict:
    bias = str(data.get("bias") or fallback["bias"]).upper()
    if bias not in ALLOWED_BIAS:
        bias = fallback["bias"]
    importance = str(data.get("importance") or fallback["importance"]).upper()
    if importance not in ALLOWED_IMP:
        importance = fallback["importance"]
    confidence = str(data.get("confidence") or fallback["confidence"]).upper()
    if confidence not in ALLOWED_CONF:
        confidence = fallback["confidence"]
    analysis_ru = data.get("analysis_ru") or fallback["analysis_ru"]
    impact = data.get("assets_impact") if isinstance(data.get("assets_impact"), dict) else fallback["impact"]
    clean_impact = {}
    for k, v in (impact or {}).items():
        vv = str(v).upper()
        clean_impact[str(k)[:32]] = vv if vv in ALLOWED_BIAS else "UNCERTAIN"
    return {
        "bias": bias,
        "importance": importance,
        "confidence": confidence,
        "analysis_ru": str(analysis_ru)[:1200],
        "impact": clean_impact,
        "category": fallback["category"],
        "assets": fallback["assets"],
        "method": data.get("method") or fallback.get("method", "rule-based"),
    }


async def analyze(
    item: RawNews,
    category: str,
    assets: List[str],
) -> Dict[str, Any]:
    text = f"{item.title}. {item.summary}"
    bias = _bias_from_text(text)
    importance = _importance(text, category)
    confidence = "LOW" if bias in ("NEUTRAL", "UNCERTAIN") else "MEDIUM"
    impact = {a: bias for a in assets} if assets else {"MARKET": bias}

    # Technical / sentiment without market data → unavailable
    if category in ("technical", "sentiment"):
        analysis_ru = (
            f"Категория {CATEGORIES.get(category, {}).get('name_ru', category)}: "
            "для сигналов нужны рыночные данные. Сейчас: DATA UNAVAILABLE. "
            "Заголовок не используется как техсигнал."
        )
        return {
            "bias": "UNCERTAIN",
            "importance": "LOW",
            "confidence": "LOW",
            "impact": {},
            "analysis_ru": analysis_ru,
            "category": category,
            "assets": [],
            "method": "unavailable",
        }

    analysis_ru = (
        f"Событие: категория {CATEGORIES.get(category, {}).get('name_ru', category)}. "
        f"Направление (эвристика): {bias}. "
        f"Активы: {', '.join(assets) if assets else 'не определены'}. "
        f"Без выдуманных цифр. При нехватке данных — Uncertain."
    )

    fallback = {
        "bias": bias,
        "importance": importance,
        "confidence": confidence,
        "impact": impact,
        "analysis_ru": analysis_ru,
        "category": category,
        "assets": assets,
        "method": "rule-based",
    }

    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            prompt = (
                "You are a professional financial news analyst.\n"
                "Rules: Use ONLY the provided title and text. "
                "Do NOT invent prices, percentages, volumes or events. "
                "If direction is unclear, bias=UNCERTAIN. "
                "CRITICAL only for exceptional systemic events, not routine data.\n"
                "Reply JSON only:\n"
                '{"bias":"BULLISH|BEARISH|NEUTRAL|UNCERTAIN",'
                '"importance":"LOW|MEDIUM|HIGH|CRITICAL",'
                '"confidence":"LOW|MEDIUM|HIGH",'
                '"analysis_ru":"2-4 sentences in Russian: what happened, why it matters, '
                'short-term vs medium-term impact",'
                '"assets_impact":{"ASSET":"BULLISH|BEARISH|NEUTRAL|UNCERTAIN"},'
                '"method":"openai"}'
                f"\n\nTitle: {item.title}\nText: {item.summary[:2000]}\n"
                f"Category: {category}\nSuggested assets: {assets}"
            )
            resp = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            data["method"] = "openai"
            return _validate_analysis(data, fallback)
        except Exception as e:
            logger.warning(f"AI analyze fallback to rules: {e}")

    return fallback
