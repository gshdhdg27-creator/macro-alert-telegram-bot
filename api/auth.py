"""Telegram WebApp initData HMAC verification.
Never trust initDataUnsafe or client-supplied user id alone.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

from bot.config import get_settings


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


def verify_init_data(
    init_data: str,
    bot_token: Optional[str] = None,
    max_age_seconds: int = 86400,
) -> TelegramUser:
    """
    Validate Telegram Mini App initData per official docs:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not isinstance(init_data, str):
        raise AuthError("Missing initData")

    token = bot_token or get_settings().bot_token
    if not token:
        raise AuthError("Server misconfigured", 500)

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise AuthError("Missing hash")

    # Data-check-string: key=value sorted by key, joined with \n
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise AuthError("Invalid initData signature")

    auth_date = parsed.get("auth_date")
    try:
        auth_ts = int(auth_date)
    except (TypeError, ValueError):
        raise AuthError("Invalid auth_date")

    if max_age_seconds > 0 and (time.time() - auth_ts) > max_age_seconds:
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
