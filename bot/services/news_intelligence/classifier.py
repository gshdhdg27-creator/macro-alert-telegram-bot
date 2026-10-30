"""Classify news into categories — keyword based, no invented labels."""
from __future__ import annotations

from typing import List, Tuple

from bot.services.news_intelligence.categories import CATEGORIES
from bot.services.news_intelligence.collector import RawNews


def classify(item: RawNews) -> Tuple[str, List[str]]:
    """Return (primary_category_id, matched_assets)."""
    text = f"{item.title} {item.summary}".lower()
    scores = {}
    assets: List[str] = []
    for cat_id, cat in CATEGORIES.items():
        score = 0
        for kw in cat["keywords"]:
            if kw.lower() in text:
                score += 1
        if score:
            scores[cat_id] = score
            for a in cat.get("assets") or []:
                if a not in assets:
                    assets.append(a)
    if not scores:
        return "economic", assets
    primary = max(scores, key=scores.get)
    return primary, assets
