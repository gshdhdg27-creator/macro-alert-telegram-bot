"""AI / rule-based market analysis. Never invents prices or events."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from loguru import logger

from bot.config import get_settings
from bot.services.news_intelligence.categories import CATEGORIES
from bot.services.news_intelligence.collector import RawNews

settings = get_settings()

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
    if b > r and b > 0:
        return "BULLISH"
    if r > b and r > 0:
        return "BEARISH"
    if b == r and b > 0:
        return "UNCERTAIN"
    return "NEUTRAL"


def _importance(text: str, category: str) -> str:
    t = text.lower()
    critical_kw = [
        "rate decision", "emergency", "crash", "default", "war", "nfp", "fomc",
        "cpi ", "interest rate", "hack", "etf approved",
    ]
    high_kw = ["fed", "ecb", "powell", "inflation", "gdp", "unemployment", "bitcoin"]
    if any(k in t for k in critical_kw):
        return "CRITICAL"
    if category in ("central_banks", "economic") or any(k in t for k in high_kw):
        return "HIGH"
    if category in ("geopolitics", "whales", "crypto"):
        return "MEDIUM"
    return "MEDIUM"


async def analyze(
    item: RawNews,
    category: str,
    assets: List[str],
) -> Dict[str, Any]:
    """Return structured analysis. Uses OpenAI if key set, else rules."""
    text = f"{item.title}. {item.summary}"
    bias = _bias_from_text(text)
    importance = _importance(text, category)

    impact = {a: bias for a in assets} if assets else {"MARKET": bias}

    analysis_ru = (
        f"Событие относится к категории {CATEGORIES.get(category, {}).get('name_ru', category)}. "
        f"Оценка влияния: {bias}. "
        f"Затронутые активы: {', '.join(assets) if assets else 'рынок в целом'}. "
        f"Вывод основан только на тексте источника, без выдуманных цифр."
    )

    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            prompt = (
                "You are a financial news analyst. Analyze ONLY the given text. "
                "Do not invent numbers, prices or events. Reply JSON: "
                '{"bias":"BULLISH|BEARISH|NEUTRAL|UNCERTAIN","importance":"LOW|MEDIUM|HIGH|CRITICAL",'
                '"analysis_ru":"2-3 sentences in Russian","assets_impact":{"ASSET":"BULLISH|..."}}'
                f"\n\nTitle: {item.title}\nText: {item.summary[:2000]}\nCategory: {category}\nAssets: {assets}"
            )
            resp = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=350,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            bias = data.get("bias") or bias
            importance = data.get("importance") or importance
            analysis_ru = data.get("analysis_ru") or analysis_ru
            if isinstance(data.get("assets_impact"), dict):
                impact = data["assets_impact"]
        except Exception as e:
            logger.warning(f"AI analyze fallback: {e}")

    return {
        "bias": bias,
        "importance": importance,
        "impact": impact,
        "analysis_ru": analysis_ru,
        "category": category,
        "assets": assets,
    }
