"""Telegram initData verification tests."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from api.auth import AuthError, verify_init_data

BOT_TOKEN = "123456:ABC-DEF_test_token_for_hmac"


def _make_init_data(user: dict, auth_date: int | None = None, bot_token: str = BOT_TOKEN, tamper: bool = False) -> str:
    auth_date = auth_date if auth_date is not None else int(time.time())
    fields = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, separators=(",", ":")),
        "query_id": "AAEAAAE",
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        h = "0" * 64
    fields["hash"] = h
    return urlencode(fields)


def test_valid_init_data(monkeypatch):
    from bot import config as cfg

    class S:
        bot_token = BOT_TOKEN
        admin_id = 42

    monkeypatch.setattr(cfg, "get_settings", lambda: S())
    raw = _make_init_data({"id": 42, "username": "admin", "first_name": "A"})
    user = verify_init_data(raw, bot_token=BOT_TOKEN)
    assert user.id == 42
    assert user.username == "admin"


def test_invalid_hash(monkeypatch):
    from bot import config as cfg

    class S:
        bot_token = BOT_TOKEN
        admin_id = 42

    monkeypatch.setattr(cfg, "get_settings", lambda: S())
    raw = _make_init_data({"id": 42}, tamper=True)
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN)
    assert "Invalid" in ei.value.message


def test_expired_init_data(monkeypatch):
    from bot import config as cfg

    class S:
        bot_token = BOT_TOKEN
        admin_id = 42

    monkeypatch.setattr(cfg, "get_settings", lambda: S())
    raw = _make_init_data({"id": 42}, auth_date=int(time.time()) - 999999)
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN, max_age_seconds=3600)
    assert "expired" in ei.value.message.lower()


def test_unauthorized_user(monkeypatch):
    from bot import config as cfg

    class S:
        bot_token = BOT_TOKEN
        admin_id = 42

    monkeypatch.setattr(cfg, "get_settings", lambda: S())
    raw = _make_init_data({"id": 999})
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN)
    assert ei.value.status_code == 403


def test_modified_user_breaks_hash(monkeypatch):
    from bot import config as cfg

    class S:
        bot_token = BOT_TOKEN
        admin_id = 42

    monkeypatch.setattr(cfg, "get_settings", lambda: S())
    raw = _make_init_data({"id": 42})
    # rewrite user id in query without updating hash
    bad = raw.replace("42", "99")
    with pytest.raises(AuthError):
        verify_init_data(bad, bot_token=BOT_TOKEN)
