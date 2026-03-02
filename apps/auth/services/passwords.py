import re

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

AUTH_SETTINGS = settings.AUTH
PASSWORD_LENGTH_MIN = AUTH_SETTINGS["PASSWORD_LENGTH_MIN"]
PASSWORD_LENGTH_MAX = AUTH_SETTINGS["PASSWORD_LENGTH_MAX"]


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
    except ValidationError as e:
        return False, {"error": list(e.messages)}

    return True, None
