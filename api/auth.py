"""Telegram WebApp initData HMAC verification (official algorithm).

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

secret_key = HMAC_SHA256(<bot_token>, "WebAppData")
hash       = HMAC_SHA256(secret_key, data_check_string)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

from bot.config import get_settings

# Configurable lifetime (seconds). Default 1 hour.
DEFAULT_MAX_AGE = int(os.getenv("INITDATA_MAX_AGE", "3600"))
# Reject auth_date more than this many seconds in the future (clock skew).
MAX_FUTURE_SKEW = int(os.getenv("INITDATA_MAX_FUTURE_SKEW", "120"))


@dataclass
class TelegramUser:
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language_code: Optional[str] = None


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def compute_webapp_hash(data_check_string: str, bot_token: str) -> str:
    """Official Telegram Mini App HMAC.

    secret_key = HMAC_SHA256(key=bot_token, message=b"WebAppData")
    hash       = HMAC_SHA256(key=secret_key, message=data_check_string)
    """
    secret_key = hmac.new(
        bot_token.encode("utf-8"),
        b"WebAppData",
        hashlib.sha256,
    ).digest()
    return hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_init_data(
    init_data: str,
    bot_token: Optional[str] = None,
    max_age_seconds: Optional[int] = None,
) -> TelegramUser:
    if not init_data or not isinstance(init_data, str):
        raise AuthError("Missing initData")

    token = bot_token or get_settings().bot_token
    if not token:
        raise AuthError("Server misconfigured", 500)

    max_age = DEFAULT_MAX_AGE if max_age_seconds is None else max_age_seconds

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise AuthError("Missing hash")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    calculated = compute_webapp_hash(data_check, token)

    if not hmac.compare_digest(calculated, received_hash):
        raise AuthError("Invalid initData signature")

    auth_date = parsed.get("auth_date")
    try:
        auth_ts = int(auth_date)
    except (TypeError, ValueError):
        raise AuthError("Invalid auth_date")

    now = time.time()
    if auth_ts - now > MAX_FUTURE_SKEW:
        raise AuthError("auth_date is in the future")
    if max_age > 0 and (now - auth_ts) > max_age:
        raise AuthError("initData expired", 401)

    user_raw = parsed.get("user")
    if not user_raw:
        raise AuthError("Missing user")

    try:
        user_obj = json.loads(user_raw)
        uid = int(user_obj["id"])
    except Exception:
        raise AuthError("Invalid user payload")

    settings = get_settings()
    if settings.admin_id and uid != settings.admin_id:
        raise AuthError("Forbidden", 403)

    return TelegramUser(
        id=uid,
        username=user_obj.get("username"),
        first_name=user_obj.get("first_name"),
        language_code=user_obj.get("language_code"),
    )
