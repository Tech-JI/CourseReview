import hashlib
import json
import logging
import secrets
import time

from django.conf import settings
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

AUTH_SETTINGS = settings.AUTH
OTP_TIMEOUT = AUTH_SETTINGS["OTP_TIMEOUT"]
TEMP_TOKEN_TIMEOUT = AUTH_SETTINGS["TEMP_TOKEN_TIMEOUT"]


def get_auth_redis():
    return get_redis_connection("default")


def get_client_ip(request) -> str | None:
    return (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )


def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_state_key(temp_token: str) -> str:
    return f"temp_token_state:{get_token_hash(temp_token)}"


def generate_otp(length: int = 8) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def generate_temp_token() -> str:
    return secrets.token_urlsafe(32)


def cleanup_existing_temp_token(redis_client, temp_token: str | None) -> None:
    # Clean up any existing temp_token for this client to prevent memory leaks
    if not temp_token:
        return

    try:
        existing_state_key = get_state_key(temp_token)
        existing_state_data = redis_client.get(existing_state_key)

        if existing_state_data:
            existing_state = json.loads(existing_state_data)
            action = (
                existing_state.get("action", "unknown")
                if isinstance(existing_state, dict)
                else "unknown"
            )

            redis_client.delete(existing_state_key)
            logger.info(
                "Cleaned up existing temp_token_state for action %s",
                action,
            )

    except Exception:
        logger.warning("Error cleaning up existing temp_token")


def store_auth_intent(redis_client, otp: str, temp_token: str, action: str) -> None:
    # Store OTP -> temp_token mapping with initiated_at timestamp
    current_time = time.time()
    otp_data = {"temp_token": temp_token, "initiated_at": current_time}
    redis_client.setex(f"otp:{otp}", OTP_TIMEOUT, json.dumps(otp_data))

    # Store temp_token with SHA256 hash as key, and status of pending as well as action
    temp_token_state = {"status": "pending", "action": action}
    redis_client.setex(
        get_state_key(temp_token),
        TEMP_TOKEN_TIMEOUT,
        json.dumps(temp_token_state),
    )
