"""send_alert_to_user returns True only on successful delivery."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.services.alert_service import _tags_match_subscriptions


def test_subscription_helpers():
    assert _tags_match_subscriptions("BTC", {"btc": True}) is True
    assert _tags_match_subscriptions("BTC", {"btc": False}) is False
    assert _tags_match_subscriptions("", {"btc": False}) is True


@pytest.mark.asyncio
async def test_send_returns_false_without_user(monkeypatch):
    from bot.services import alert_service as mod

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeSession:
        async def execute(self, *a, **k):
            return FakeResult()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    monkeypatch.setattr(mod, "async_session", lambda: FakeSession())
    bot = AsyncMock()
    ok = await mod.send_alert_to_user(bot, "t", "title", "body")
    assert ok is False
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_quiet_mode_false(monkeypatch):
    from bot.services import alert_service as mod

    user = MagicMock()
    user.notifications_enabled = True
    user.quiet_mode = True
    user.only_high_impact = False
    user.subscribed_assets = {}

    class FakeResult:
        def scalar_one_or_none(self):
            return user

    class FakeSession:
        async def execute(self, *a, **k):
            return FakeResult()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    monkeypatch.setattr(mod, "async_session", lambda: FakeSession())
    bot = AsyncMock()
    ok = await mod.send_alert_to_user(bot, "t", "title", "body")
    assert ok is False


@pytest.mark.asyncio
async def test_notifications_disabled_false(monkeypatch):
    from bot.services import alert_service as mod

    user = MagicMock()
    user.notifications_enabled = False
    user.quiet_mode = False
    user.only_high_impact = False
    user.subscribed_assets = {}

    class FakeResult:
        def scalar_one_or_none(self):
            return user

    class FakeSession:
        async def execute(self, *a, **k):
            return FakeResult()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    monkeypatch.setattr(mod, "async_session", lambda: FakeSession())
    bot = AsyncMock()
    ok = await mod.send_alert_to_user(bot, "t", "title", "body")
    assert ok is False


@pytest.mark.asyncio
async def test_success_true(monkeypatch):
    from bot.services import alert_service as mod

    user = MagicMock()
    user.notifications_enabled = True
    user.quiet_mode = False
    user.only_high_impact = False
    user.subscribed_assets = {}

    class FakeResult:
        def scalar_one_or_none(self):
            return user

    class FakeSession:
        async def execute(self, *a, **k):
            return FakeResult()

        def add(self, *a, **k):
            pass

        async def commit(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

    monkeypatch.setattr(mod, "async_session", lambda: FakeSession())
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    ok = await mod.send_alert_to_user(bot, "t", "title", "body", importance="high")
    assert ok is True
    bot.send_message.assert_awaited()
