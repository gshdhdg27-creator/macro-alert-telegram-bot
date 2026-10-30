"""Unit tests: HTML escaping and Telegram formatter safety."""
import html
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.news_intelligence.formatter import _e, _safe_https, format_news_message
from bot.services.news_intelligence.collector import RawNews
from bot.services.alert_service import _tags_match_subscriptions


def test_html_escape():
    assert _e("<script>") == "&lt;script&gt;"
    assert _e("a&b") == "a&amp;b"
    assert _e('"') == "&quot;"


def test_safe_https():
    assert _safe_https("https://example.com/x") == "https://example.com/x"
    assert _safe_https("http://example.com") is None
    assert _safe_https("javascript:alert(1)") is None
    assert _safe_https(None) is None


def test_format_escapes_title():
    item = RawNews(
        id="1",
        title="<b>Hack</b> & crash",
        summary="Desc <img>",
        link="https://example.com/news",
        source="Test",
        published=None,
    )
    analysis = {
        "category": "crypto",
        "bias": "BEARISH",
        "importance": "HIGH",
        "confidence": "LOW",
        "method": "rule-based",
        "impact": {"BTC": "BEARISH"},
        "assets": ["BTC"],
        "analysis_ru": "Test <analysis>",
    }
    text = format_news_message(item, analysis)
    assert "<b>Hack</b>" not in text or "&lt;b&gt;Hack&lt;/b&gt;" in text
    assert "&lt;b&gt;Hack&lt;/b&gt;" in text
    assert "&amp;" in text
    assert "https://example.com/news" in text


def test_subscription_filter():
    sub = {"btc": True, "eth": False}
    assert _tags_match_subscriptions("BTC,CRYPTO", sub) is True
    assert _tags_match_subscriptions("EURUSD", {"btc": True}) is False
    assert _tags_match_subscriptions("", sub) is True


if __name__ == "__main__":
    test_html_escape()
    test_safe_https()
    test_format_escapes_title()
    test_subscription_filter()
    print("ALL TESTS PASSED")
