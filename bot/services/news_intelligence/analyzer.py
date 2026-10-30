"""AI / rule-based market analysis. Never invents prices, facts or events."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from loguru import logger

from bot.config import get_settings
from bot.services.news_intelligence.categories import CATEGORIES
from bot.services.news_intelligence.collector import RawNews

settings = get_settings()

# Keyword hints are a weak prior only — not definitive direction
BULLISH_HINTS = [
    "surge", "rally", "rise", "gain", "beat", "stronger", "growth", "approval",
    "inflow", "record high", "boost", "optimistic", "cut rates", "stimulus",
]
BEARISH_HINTS = [
    "fall", "drop", "plunge", "decline", "miss", "weaker", "recession", "sanction",
    "outflow", "hack", "ban", "hike rates", "inflation jump", "layoff", "crisis",
]


def _bias_from_text(text: str) -> str:
    """Weak heuristic. Prefer UNCERTAIN when signals conflict or are weak."""
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
    """Structured analysis. OpenAI if key set; else conservative rules. No invented facts."""
    text = f"{item.title}. {item.summary}"
    bias = _bias_from_text(text)
    importance = _importance(text, category)
    confidence = "LOW" if bias in ("NEUTRAL", "UNCERTAIN") else "MEDIUM"

    impact = {a: bias for a in assets} if assets else {"MARKET": bias}

    analysis_ru = (
        f"Событие: категория {CATEGORIES.get(category, {}).get('name_ru', category)}. "
        f"Направление (эвристика по тексту): {bias}. "
        f"Активы: {', '.join(assets) if assets else 'рынок в целом'}. "
        f"Без выдуманных цифр и цен. При нехватке данных — Uncertain."
    )

    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            prompt = (
                "You are a professional financial news analyst.\n"
                "Rules:\n"
                "- Use ONLY the provided title and text.\n"
                "- Do NOT invent prices, percentages, volumes or events.\n"
                "- If direction is unclear, set bias to UNCERTAIN.\n"
                "- confidence: LOW|MEDIUM|HIGH based on text clarity.\n"
                "Reply JSON only:\n"
                '{"bias":"BULLISH|BEARISH|NEUTRAL|UNCERTAIN",'
                '"importance":"LOW|MEDIUM|HIGH|CRITICAL",'
                '"confidence":"LOW|MEDIUM|HIGH",'
                '"analysis_ru":"2-4 sentences in Russian: what happened, why it matters, short-term vs medium-term impact",'
                '"assets_impact":{"ASSET":"BULLISH|BEARISH|NEUTRAL|UNCERTAIN"}}'
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
            bias = data.get("bias") or bias
            importance = data.get("importance") or importance
            confidence = data.get("confidence") or confidence
            analysis_ru = data.get("analysis_ru") or analysis_ru
            if isinstance(data.get("assets_impact"), dict) and data["assets_impact"]:
                impact = data["assets_impact"]
        except Exception as e:
            logger.warning(f"AI analyze fallback to rules: {e}")

    return {
        "bias": bias,
        "importance": importance,
        "confidence": confidence,
        "impact": impact,
        "analysis_ru": analysis_ru,
        "category": category,
        "assets": assets,
    }
