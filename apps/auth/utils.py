import json
import logging
import re
import time
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django_redis import get_redis_connection
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response

from apps.web.models import Student

logger = logging.getLogger(__name__)

AUTH_SETTINGS = settings.AUTH
PASSWORD_LENGTH_MIN = AUTH_SETTINGS["PASSWORD_LENGTH_MIN"]
PASSWORD_LENGTH_MAX = AUTH_SETTINGS["PASSWORD_LENGTH_MAX"]
OTP_TIMEOUT = int(AUTH_SETTINGS["OTP_TIMEOUT"])
EMAIL_DOMAIN_NAME = AUTH_SETTINGS["EMAIL_DOMAIN_NAME"]

QUEST_SETTINGS = settings.QUEST
QUEST_BASE_URL = QUEST_SETTINGS["BASE_URL"]


class CSRFCheckSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        super().enforce_csrf(request)
        return super().authenticate(request)


def get_survey_details(action: str) -> dict[str, Any] | None:
    """
    A single, clean function to get all survey details for a given action.
    Valid actions: "signup", "login", "reset_password".
    """

    action_details = QUEST_SETTINGS.get(action.upper())

    if not action_details:
        logger.error("Invalid quest action requested: %s", action)
        return None

    try:
        question_id = int(action_details.get("QUESTIONID"))
    except (ValueError, TypeError):  # fmt: skip
        logger.error(
            "Could not parse 'QUESTIONID' for action '%s'. Check your settings.", action
        )
        return None

    return {
        "url": action_details.get("URL"),
        "api_key": action_details.get("API_KEY"),
        "question_id": question_id,
    }


async def verify_turnstile_token(
    turnstile_token, client_ip
) -> tuple[bool, Response | None]:
    """Helper function to verify Turnstile token with Cloudflare's API"""

    try:
        async with httpx.AsyncClient(timeout=OTP_TIMEOUT) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": turnstile_token,
                    "remoteip": client_ip,
                },
            )
        if not response.json().get("success"):
            logger.warning("Turnstile verification failed: %s", response.json())
            return False, Response(
                {"error": "Turnstile verification failed"}, status=403
            )
        return True, None
    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out")
        return False, Response(
            {"error": "Turnstile verification timed out"}, status=504
        )
    except Exception:
        logger.error("Turnstile verification error")
        return False, Response({"error": "Turnstile verification error"}, status=500)


WJ_CLOCK_OFFSET_KEY = "wj:clock:offset"
WJ_CLOCK_OFFSET_TTL = 48 * 3600
WJ_CLOCK_EWMA_ALPHA = 0.3


def estimate_wj_clock_offset(response: httpx.Response) -> float | None:
    """Estimate WJ server clock offset (wj_time - local_time) in seconds.

    Negative means the WJ clock runs slow (currently ~-230s and drifting
    ~7s/day). Derived from the response `Date` header with request-RTT
    midpoint correction. The `Date` header and the `submitted_at` field
    come from the same WJ server clock domain (verified 2026-09-08: header
    offset matches the measured submitted_at drift history), so this offset
    corrects `submitted_at` before validity-window checks.
    """
    date_str = response.headers.get("date")
    if not date_str:
        return None
    try:
        wj_time = parsedate_to_datetime(date_str)
    except (TypeError, ValueError):  # fmt: skip
        return None
    if wj_time is None:  # fmt: skip
        return None
    try:
        elapsed = response.elapsed.total_seconds()
    except (RuntimeError, AttributeError):  # fmt: skip
        elapsed = 0.0
    receive_time = time.time()
    send_time = receive_time - elapsed
    local_midpoint = (send_time + receive_time) / 2.0
    return wj_time.timestamp() - local_midpoint


def record_wj_clock_offset(offset: float) -> None:
    """Fold a fresh offset sample into the rolling EWMA estimate in Redis."""
    try:
        r = get_redis_connection("default")
        existing = r.hget(WJ_CLOCK_OFFSET_KEY, "offset")
        if existing is not None:
            offset = WJ_CLOCK_EWMA_ALPHA * offset + (1 - WJ_CLOCK_EWMA_ALPHA) * float(
                existing
            )
        r.hset(
            WJ_CLOCK_OFFSET_KEY, mapping={"offset": offset, "updated_at": time.time()}
        )
        r.expire(WJ_CLOCK_OFFSET_KEY, WJ_CLOCK_OFFSET_TTL)
    except Exception:
        logger.warning("Failed to record WJ clock offset", exc_info=True)


def get_cached_wj_clock_offset() -> float | None:
    """Rolling EWMA offset estimate from Redis, or None if unavailable/stale."""
    try:
        r = get_redis_connection("default")
        cached = r.hget(WJ_CLOCK_OFFSET_KEY, "offset")
        return float(cached) if cached is not None else None
    except Exception:
        return None


async def get_latest_answer(
    action: str,
    account: str,
) -> tuple[dict | None, Response | None]:
    """Fetch the latest questionnaire answer for a given account from the WJ API(specific api for actions).
    Returns a tuple of (filtered_data, error_response).
    `filtered_data` contains: id, submitted_at, user.account, and otp.
    `error_response` is a DRF Response object if an error occurs, otherwise None.
    """

    details = get_survey_details(action)
    if not details:
        return None, Response({"error": "Invalid action"}, status=400)
    quest_api = details.get("api_key")
    if not quest_api:
        return None, Response({"error": "Invalid action"}, status=400)

    # Get the target question ID for the verification code
    question_id = details.get("question_id")
    if not question_id:
        return None, Response(
            {"error": "Configuration error: question ID not found for action"},
            status=500,
        )

    # Build the 'params' and 'sort' dictionaries
    params_dict = {
        "account": account,
        "current": 1,
        "pageSize": 1,
    }
    sort_dict = {"id": "desc"}

    params_json_str = json.dumps(params_dict, ensure_ascii=False)
    sort_json_str = json.dumps(sort_dict)

    # Prepare the final query parameters
    final_query_params = {"params": params_json_str, "sort": sort_json_str}

    # Combine to form the full URL path
    full_url_path = f"{QUEST_BASE_URL}/{quest_api}/json"

    try:
        async with httpx.AsyncClient(timeout=OTP_TIMEOUT) as client:
            response = await client.get(
                full_url_path,
                params=final_query_params,
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            full_data = response.json()
            offset_sample = estimate_wj_clock_offset(response)
            if offset_sample is not None:
                record_wj_clock_offset(offset_sample)
    except httpx.TimeoutException:
        logger.error("Questionnaire API query timed out")
        return None, Response(
            {"error": "Questionnaire API query timed out"},
            status=504,
        )
    except httpx.RequestError:
        logger.error("Error querying questionnaire API")
        return None, Response(
            {"error": "Failed to query questionnaire API"},
            status=500,
        )
    except Exception:
        logger.error("An unexpected error occurred")
        return None, Response({"error": "An unexpected error occurred"}, status=500)

    # Filter and return only the required fields from the first row
    if (
        full_data.get("success")
        and full_data.get("data")
        and full_data["data"].get("rows")
        and len(full_data["data"]["rows"]) > 0
    ):
        # Get the first (latest) row
        latest_answer = full_data["data"]["rows"][0]

        # Find the otp by matching the question ID
        otp = None
        answers = latest_answer.get("answers", [])
        for ans in answers:
            if str(ans.get("question", {}).get("id")) == str(question_id):
                otp = ans.get("answer")
                break

        # Extract only the required fields from this row
        filtered_data = {
            "id": latest_answer.get("id"),
            "submitted_at": latest_answer.get("submitted_at"),
            "account": latest_answer.get("user", {}).get("account")
            if latest_answer.get("user")
            else None,
            "otp": otp,
            # WJ clock offset measured from this response's Date header
            # (may be None if header missing/unparseable)
            "server_clock_offset": offset_sample,
        }

        # Check if all required fields are present
        if not all(
            key in filtered_data and filtered_data[key] is not None
            for key in ["id", "submitted_at", "account", "otp"]
        ):
            logger.warning("Missing required field(s) in questionnaire response")
            return None, Response(
                {"error": "Missing required field(s) in questionnaire response"},
                status=400,
            )

        return filtered_data, None

    return None, Response(
        {"error": "No questionnaire submission found or submission invalid"},
        status=403,
    )


def rate_password_strength(password: str) -> int:
    """Helper function to rate password strength"""

    if len(password) < PASSWORD_LENGTH_MIN or len(password) > PASSWORD_LENGTH_MAX:
        return 0

    score = 1

    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^a-zA-Z0-9\s]", password):
        score += 1

    length_range = max(1, PASSWORD_LENGTH_MAX - PASSWORD_LENGTH_MIN)
    length_step = max(1, length_range // 10)

    score += (len(password) - PASSWORD_LENGTH_MIN) // length_step

    return min(score, 5)


def validate_password_strength(password: str) -> tuple[bool, dict | None]:
    """Helper function to validate password complexity and strength.

    Returns: A tuple of (is_valid, error_response).
    `is_valid` is True if the password is valid, otherwise False.
    `error_response` is a dict with a detailed error message if invalid, otherwise None.
    """

    score = rate_password_strength(password)

    if score == 0:
        return False, {
            "error": "Password is too short or too long.",
        }

    if score < 3:
        return False, {
            "error": "Password is too weak.",
        }

    # Use Django's built-in validators for additional checks
    try:
        validate_password(password)
        return True, None
    except ValidationError as e:
        return False, {"error": list(e.messages)}


def create_user_session(
    request,
    account,
) -> tuple[AbstractUser | None, Response | None]:
    """Helper function includes session management, user creation and Student model integration.
    Returns a tuple of (user, error_response).
    `user` is the user object on success, otherwise None.
    `error_response` is a DRF Response object if an error occurs, otherwise None.
    """

    try:
        # Ensure session exists - create one if it doesn't exist
        if not request.session.session_key:
            request.session.create()

        # Get or create user
        user_model = get_user_model()

        user, _ = user_model.objects.get_or_create(
            username=account,
            defaults={"email": f"{account}@{EMAIL_DOMAIN_NAME}"},
        )

        if not user:
            return None, Response(
                {"error": "Failed to retrieve or create user"}, status=500
            )

        # Handle Student model integration
        Student.objects.get_or_create(user=user)

        # Update session to use authenticated username
        request.session["user_id"] = user.username
        return user, None

    except Exception:
        return None, Response({"error": "Failed to create user session"}, status=500)
