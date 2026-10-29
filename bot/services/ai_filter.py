import json
from typing import Optional, Dict, Any

from openai import AsyncOpenAI
from loguru import logger

from bot.config import get_settings, ASSETS

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None


SYSTEM_PROMPT = """You are a financial news filter and summarizer for a professional trader.
Your tasks:
1. Decide if the news is IMPORTANT (true breaking / high-impact) or NOISE.
2. Assign relevant asset tags from the allowed list.
3. Write a very short summary (2-3 sentences) in the requested language.

Allowed asset tags: XAUUSD, NASDAQ, SP500, BTC, ETH, DXY, OIL, EURUSD, GBPUSD, USDJPY, AGRO, TSLA, AI_TECH

Respond ONLY with valid JSON:
{
  "important": true/false,
  "importance": "high" | "medium" | "low",
  "tags": ["XAUUSD", "DXY"],
  "summary_ru": "...",
  "summary_en": "..."
}
"""


async def filter_and_summarize(
    title: str,
    content: str,
    source: str = "",
    lang: str = "ru",
) -> Optional[Dict[str, Any]]:
    """
    Returns structured filter result or None if noise / error.
    """
    if not client:
        # Fallback without AI — simple keyword matching
        return _keyword_fallback(title, content)

    try:
        user_content = f"Source: {source}\nTitle: {title}\n\nContent:\n{content[:3000]}"

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)

        if not data.get("important", False):
            return None

        return data

    except Exception as e:
        logger.error(f"AI filter error: {e}")
        return _keyword_fallback(title, content)


def _keyword_fallback(title: str, content: str) -> Optional[Dict[str, Any]]:
    text = (title + " " + content).lower()
    matched_tags = []

    for key, asset in ASSETS.items():
        for kw in asset["keywords"]:
            if kw.lower() in text:
                matched_tags.extend(asset["tags"][:1])
                break

    if not matched_tags:
        return None

    return {
        "important": True,
        "importance": "medium",
        "tags": list(set(matched_tags))[:3],
        "summary_ru": title,
        "summary_en": title,
    }
