"""Calendar HTML escaping — security properties, not substring bans."""
import html
import re

from bot.services.calendar_service import _e, stable_event_id


def test_escape_script_tags():
    escaped = _e("<script>alert(1)</script>")
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert escaped == html.escape("<script>alert(1)</script>", quote=True)


def test_escape_amp():
    assert "&amp;" in _e("A & B")


def test_escape_quotes_for_attributes():
    escaped = _e('USD" onclick="x')
    assert "&quot;" in escaped
    # raw double-quote characters must not remain unescaped
    assert '"' not in escaped


def test_img_onerror_not_executable_markup():
    name = '<img src=x onerror=alert(1)>'
    currency = 'USD" onclick="evil'
    # Only our intentional Telegram tags around escaped content
    line = f"⭐️ <b>{_e(currency)}</b> | {_e(name)}"
    assert "<img" not in line
    assert "&lt;img" in line
    assert "&quot;" in line
    # Untrusted content must not introduce angle-bracket tags
    # Strip our own <b>...</b> wrappers and ensure no remaining '<' from payload
    stripped = re.sub(r"</?b>", "", line)
    assert "<" not in stripped


def test_stable_event_id_consistent():
    a = stable_event_id("CPI", "2026-01-01T12:00:00", "USD")
    b = stable_event_id("CPI", "2026-01-01T12:00:00", "USD")
    c = stable_event_id("CPI", "2026-01-01T12:00:00", "EUR")
    assert a == b
    assert a != c
    assert len(a) == 32
