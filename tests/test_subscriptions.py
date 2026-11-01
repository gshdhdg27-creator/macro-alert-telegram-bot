"""Subscription filtering shared by alerts and publisher."""
from bot.services.alert_service import _tags_match_subscriptions


def test_match_btc():
    assert _tags_match_subscriptions("BTC,CRYPTO", {"btc": True, "eth": False}) is True


def test_no_match():
    assert _tags_match_subscriptions("EURUSD", {"btc": True}) is False


def test_empty_tags_broadcast():
    assert _tags_match_subscriptions("", {"btc": True}) is True


def test_empty_subs_allow():
    assert _tags_match_subscriptions("BTC", {}) is True


def test_all_disabled():
    # matching function returns False when no enabled asset matches
    assert _tags_match_subscriptions("BTC", {"btc": False, "eth": False}) is False
