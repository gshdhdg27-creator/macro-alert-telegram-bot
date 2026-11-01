"""Independent tests for official Telegram WebApp HMAC."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from api.auth import AuthError, compute_webapp_hash, verify_init_data
import api.auth as auth_mod

BOT_TOKEN = "123456:ABC-DEF_official_algo_token"


def official_sign(fields: dict, bot_token: str = BOT_TOKEN) -> str:
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(bot_token.encode("utf-8"), b"WebAppData", hashlib.sha256).digest()
    return hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()


def make_init_data(
    user: dict,
    *,
    auth_date: int | None = None,
    bot_token: str = BOT_TOKEN,
    bad_hash: str | None = None,
    omit_hash: bool = False,
) -> str:
    auth_date = int(time.time()) if auth_date is None else auth_date
    fields = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, separators=(",", ":")),
        "query_id": "AAEAAAE",
    }
    if not omit_hash:
        fields["hash"] = bad_hash if bad_hash is not None else official_sign(fields, bot_token)
    return urlencode(fields)


class _Settings:
    bot_token = BOT_TOKEN
    admin_id = 42


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr(auth_mod, "get_settings", lambda: _Settings())


def test_compute_matches_official():
    fields = {"auth_date": "1700000000", "query_id": "x", "user": '{"id":1}'}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    assert compute_webapp_hash(data_check, BOT_TOKEN) == official_sign(fields)


def test_valid_init_data():
    raw = make_init_data({"id": 42, "username": "admin", "first_name": "A"})
    user = verify_init_data(raw, bot_token=BOT_TOKEN)
    assert user.id == 42
    assert user.username == "admin"


def test_invalid_hash():
    raw = make_init_data({"id": 42}, bad_hash="0" * 64)
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN)
    assert "Invalid" in ei.value.message


def test_missing_hash():
    raw = make_init_data({"id": 42}, omit_hash=True)
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN)
    assert "hash" in ei.value.message.lower()


def test_expired():
    raw = make_init_data({"id": 42}, auth_date=int(time.time()) - 10_000)
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN, max_age_seconds=3600)
    assert "expired" in ei.value.message.lower()


def test_future_auth_date():
    raw = make_init_data({"id": 42}, auth_date=int(time.time()) + 10_000)
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN)
    assert "future" in ei.value.message.lower()


def test_modified_user_breaks_hash():
    raw = make_init_data({"id": 42})
    bad = raw.replace("%7B%22id%22%3A42", "%7B%22id%22%3A99")
    if bad == raw:
        bad = raw.replace("42", "99", 1)
    with pytest.raises(AuthError):
        verify_init_data(bad, bot_token=BOT_TOKEN)


def test_unauthorized_user():
    raw = make_init_data({"id": 999})
    with pytest.raises(AuthError) as ei:
        verify_init_data(raw, bot_token=BOT_TOKEN)
    assert ei.value.status_code == 403
