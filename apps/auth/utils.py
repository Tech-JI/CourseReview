import json
import logging
import re
from typing import Any

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.exceptions import PermissionDenied

from apps.web.models import Student
from lib.logging import add_sanitization_to_logger

logger = add_sanitization_to_logger(logging.getLogger(__name__))

AUTH_SETTINGS = settings.AUTH
PASSWORD_LENGTH_MIN = AUTH_SETTINGS["PASSWORD_LENGTH_MIN"]
PASSWORD_LENGTH_MAX = AUTH_SETTINGS["PASSWORD_LENGTH_MAX"]
OTP_TIMEOUT = AUTH_SETTINGS["OTP_TIMEOUT"]
EMAIL_DOMAIN_NAME = AUTH_SETTINGS["EMAIL_DOMAIN_NAME"]

QUEST_SETTINGS = settings.QUEST
QUEST_BASE_URL = QUEST_SETTINGS["BASE_URL"]


class CSRFCheckSessionAuthentication(SessionAuthentication):
    def authenticate(self, request):
        super().enforce_csrf(request)
        return super().authenticate(request)
    
class BusinessException(APIException):
    status_code = 400
    default_detail = "Business error"
    default_code = "business_error"


class ExternalServiceException(APIException):
    status_code = 500
    default_detail = "External service error"
    default_code = "external_error"

def get_survey_details(action: str) -> dict[str, Any]:
    """
    A single, clean function to get all survey details for a given action.
    Valid actions: "signup", "login", "reset_password".
    """

    action_details = QUEST_SETTINGS.get(action.upper())

    if not action_details:
        logger.error("Invalid quest action requested in get_survey_details: %r, valid actions: %r",          
            action, ["signup", "login", "reset_password"])
        raise ValidationError("Invalid quest action")

    try:
        question_id = int(action_details.get("QUESTIONID"))
    except (ValueError, TypeError):
        logger.error(
            "Could not parse 'QUESTIONID' for action %r (value=%r). Reason: QUESTIONID isn't a valid number. Check your settings.", action, action_details.get("QUESTIONID")
        )
        raise ValidationError("Invalid QUESTIONID configuration")

    return {
        "url": action_details.get("URL"),
        "api_key": action_details.get("API_KEY"),
        "question_id": question_id,
    }


async def verify_turnstile_token(turnstile_token, client_ip) -> None:
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
            logger.warning("Turnstile verification failed. Response: %r", response.json())
            raise PermissionDenied("Turnstile verification failed")
        
    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out after %r seconds", OTP_TIMEOUT)
        raise ExternalServiceException("Turnstile verification timed out")
    except Exception as e:
        logger.error("Turnstile verification failed with unexpected error: %r", e)
        raise ExternalServiceException("Turnstile verification error")


async def get_latest_answer(action: str, account: str) -> dict:
    """Fetch the latest questionnaire answer for a given account from the WJ API(specific api for actions).
    Returns a tuple of (filtered_data, error_response).
    `filtered_data` contains: id, submitted_at, user.account, and otp.
    `error_response` is a DRF Response object if an error occurs, otherwise None.
    """
    details = get_survey_details(action)

    quest_api = details.get("api_key")
    if not quest_api:
        raise ValidationError("Invalid action configuration")

    # Get the target question ID for the verification code
    question_id = details.get("question_id")
    if not question_id:
        raise ExternalServiceException(
            "Configuration error: question ID not found for action")

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
    except httpx.TimeoutException:
        logger.error("Questionnaire API query timed out after %r seconds for action %r, account %r", OTP_TIMEOUT, action, account)
        raise ExternalServiceException("Questionnaire API query timed out")
    except httpx.RequestError as e:
        logger.error("Failed to query questionnaire API for action %r, account %r (URL: %r, error: %r)", action, account, full_url_path, e)
        raise ExternalServiceException("Failed to query questionnaire API")
    except Exception as e:
        logger.exception("Unexpected error while ing questionnaire response for action %r, account %r: %r", action, account, e)
        raise ExternalServiceException("An unexpected error occurred")

    if not (
        full_data.get("success")
        and full_data.get("data")
        and full_data["data"].get("rows")
        and len(full_data["data"]["rows"]) > 0
    ):
        raise PermissionDenied("No questionnaire submission found")
    
    # Get the first (latest) row
    latest_answer = full_data["data"]["rows"][0]

    # Find the otp by matching the question ID
    otp = next(
        (
            ans.get("answer")
            for ans in latest_answer.get("answers", [])
            if str(ans.get("question", {}).get("id")) == str(question_id)
        ),
        None,
    )
    
    # Extract only the required fields from this row
    filtered_data = {
        "id": latest_answer.get("id"),
        "submitted_at": latest_answer.get("submitted_at"),
        "account": latest_answer.get("user", {}).get("account")
        if latest_answer.get("user")
        else None,
        "otp": otp,
    }

    # Check if all required fields are present
    required_fields = ["id", "submitted_at", "account", "otp"]

    missing_fields = [
        key for key in required_fields
        if filtered_data.get(key) is None
    ]

    if missing_fields:
        logger.warning(
            "Missing required field(s) in questionnaire response",
            extra={
                "action": action, 
                "account": account, 
                "missing_fields": missing_fields
            },
        )
        raise ValidationError(
            "Missing required field(s) in questionnaire response"
        )

    return filtered_data

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


def create_user_session(request, account) -> AbstractUser:
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
        return user

    except Exception as e:
        logger.exception("Failed to create user session")
        raise APIException("Failed to create user session")
