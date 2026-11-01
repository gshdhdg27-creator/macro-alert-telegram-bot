"""Calendar HTML escaping and stable event ids."""
import html

from bot.services.calendar_service import _e, stable_event_id


def test_escape_script():
    assert _e("<script>alert(1)</script>") == html.escape("<script>alert(1)</script>", quote=True)
    assert "<script>" not in _e("<script>")
    assert "&lt;" in _e("<b>")


def test_escape_amp():
    assert "&amp;" in _e("A & B")


def test_stable_event_id_consistent():
    a = stable_event_id("CPI", "2026-01-01T12:00:00", "USD")
    b = stable_event_id("CPI", "2026-01-01T12:00:00", "USD")
    c = stable_event_id("CPI", "2026-01-01T12:00:00", "EUR")
    assert a == b
    assert a != c
    assert len(a) == 32


def test_malicious_event_line_safe():
    name = '<img src=x onerror=alert(1)>'
    currency = 'USD" onclick="x'
    line = f"⭐️ <b>{_e(currency)}</b> | {_e(name)}"
    assert "<img" not in line
    assert "onerror" not in line
    assert "&lt;img" in line
