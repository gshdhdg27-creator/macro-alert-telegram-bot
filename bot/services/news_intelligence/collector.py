"""News collector — real RSS sources only. Never invents news."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import feedparser
from loguru import logger

RSS_SOURCES = [
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "name": "BBC Business"},
    {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "name": "CoinDesk"},
    {"url": "https://www.federalreserve.gov/feeds/press_all.xml", "name": "Federal Reserve"},
    {"url": "https://feeds.reuters.com/reuters/businessNews", "name": "Reuters Business"},
    {"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "name": "CNBC"},
]


@dataclass
class RawNews:
    id: str
    title: str
    summary: str
    link: str
    source: str
    published: Optional[datetime] = None
    image: Optional[str] = None
    raw: dict = field(default_factory=dict)


def _guid(entry: dict, source: str) -> str:
    base = entry.get("id") or entry.get("link") or entry.get("title") or ""
    return hashlib.sha1(f"{source}|{base}".encode()).hexdigest()[:24]


def _parse_date(entry: dict) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_image(entry: dict) -> Optional[str]:
    if entry.get("media_content"):
        for m in entry["media_content"]:
            if m.get("url"):
                return m["url"]
    if entry.get("media_thumbnail"):
        for m in entry["media_thumbnail"]:
            if m.get("url"):
                return m["url"]
    enc = entry.get("enclosures") or entry.get("links") or []
    for e in enc:
        href = e.get("href") or e.get("url")
        t = (e.get("type") or "")
        if href and ("image" in t or href.endswith((".jpg", ".png", ".jpeg", ".webp"))):
            return href
    return None


def collect_from_rss(max_per_feed: int = 10) -> List[RawNews]:
    """Collect real news from RSS. Empty list if sources fail — never invent."""
    items: List[RawNews] = []
    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            if getattr(feed, "bozo", False) and not feed.entries:
                logger.warning(f"RSS bozo: {src['name']}")
                continue
            for entry in feed.entries[:max_per_feed]:
                title = (entry.get("title") or "").strip()
                if not title:
                    continue
                summary = entry.get("summary") or entry.get("description") or ""
                if entry.get("content"):
                    try:
                        summary = entry["content"][0].get("value", summary)
                    except Exception:
                        pass
                if isinstance(summary, list):
                    summary = ""
                summary = re.sub(r"<[^>]+>", " ", str(summary))
                summary = re.sub(r"\s+", " ", summary).strip()[:800]
                items.append(
                    RawNews(
                        id=_guid(entry, src["name"]),
                        title=title,
                        summary=summary,
                        link=entry.get("link") or "",
                        source=src["name"],
                        published=_parse_date(entry),
                        image=_extract_image(entry),
                        raw={"feed": src["url"]},
                    )
                )
        except Exception as e:
            logger.warning(f"Collector error {src['name']}: {e}")
    logger.info(f"Collected {len(items)} raw items from RSS")
    return items
