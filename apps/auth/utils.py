import json
import logging
import re

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.response import Response

from apps.web.models import Student

PASSWORD_LENGTH_MIN = settings.AUTH["PASSWORD_LENGTH_MIN"]
OTP_TIME_OUT = settings.AUTH["OTP_TIME_OUT"]
QUEST_BASE_URL = settings.AUTH["QUEST_BASE_URL"]
EMAIL_DOMAIN_NAME = settings.AUTH["EMAIL_DOMAIN_NAME"]


def get_survey_url(action: str) -> str | None:
    """Helper function to get the survey URL based on action type"""
    if action == "signup":
        return settings.SIGNUP_QUEST_URL
    if action == "login":
        return settings.LOGIN_QUEST_URL
    if action == "reset_password":
        return settings.RESET_QUEST_URL
    return None


def get_survey_api_key(action: str) -> str | None:
    """Helper function to get the survey API key based on action type"""
    if action == "signup":
        return settings.SIGNUP_QUEST_API_KEY
    if action == "login":
        return settings.LOGIN_QUEST_API_KEY
    if action == "reset_password":
        return settings.RESET_QUEST_API_KEY
    return None


def get_survey_questionid(action: str) -> int | None:
    """Helper function to get the survey question ID for the verification code based on action type"""
    question_id_str = None
    if action == "signup":
        question_id_str = settings.SIGNUP_QUEST_QUESTIONID
    elif action == "login":
        question_id_str = settings.LOGIN_QUEST_QUESTIONID
    elif action == "reset_password":
        question_id_str = settings.RESET_QUEST_QUESTIONID

    if question_id_str:
        try:
            return int(question_id_str)
        except (ValueError, TypeError):
            return None
    return None


async def verify_turnstile_token(
    turnstile_token, client_ip
) -> tuple[bool, Response | None]:
    """Helper function to verify Turnstile token with Cloudflare's API"""

    try:
        async with httpx.AsyncClient(timeout=OTP_TIME_OUT) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": turnstile_token,
                    "remoteip": client_ip,
                },
            )
        if not response.json().get("success"):
            logging.warning(f"Turnstile verification failed: {response.json()}")
            return False, Response(
                {"error": "Turnstile verification failed"}, status=403
            )
        return True, None
    except httpx.TimeoutException:
        logging.error("Turnstile verification timed out")
        return False, Response(
            {"error": "Turnstile verification timed out"}, status=504
        )
    except Exception as e:
        logging.error(f"Error verifying Turnstile token: {e}")
        return False, Response({"error": "Turnstile verification error"}, status=500)


async def get_latest_answer(
    action: str,
    account: str,
) -> tuple[dict | None, Response | None]:
    """Fetch the latest questionnaire answer for a given account from the WJ API(specific api for actions).
    Returns a tuple of (filtered_data, error_response).
    `filtered_data` contains: id, submitted_at, user.account, and otp.
    `error_response` is a DRF Response object if an error occurs, otherwise None.
    """
    quest_api = get_survey_api_key(action)
    if not quest_api:
        return None, Response({"error": "Invalid action"}, status=400)

    # Get the target question ID for the verification code
    question_id = get_survey_questionid(action)
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
        async with httpx.AsyncClient(timeout=OTP_TIME_OUT) as client:
            response = await client.get(
                full_url_path,
                params=final_query_params,
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            full_data = response.json()
    except httpx.TimeoutException:
        logging.exception("Questionnaire API query timed out")
        return None, Response(
            {"error": "Questionnaire API query timed out"},
            status=504,
        )
    except httpx.RequestError as e:
        logging.exception(f"Error querying questionnaire API: {e}")
        return None, Response(
            {"error": "Failed to query questionnaire API"},
            status=500,
        )
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return None, Response({"error": "An unexpected error occurred"}, status=500)

    # Filter and return only the required fields from the first row
    if (
        full_data.get("success")
        and full_data.get("data")
        and full_data["data"].get("rows")
        and len(full_data["data"]["rows"]) > 0
    ):
        latest_answer = full_data["data"]["rows"][0]  # Get the first (latest) row

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
        }

        # Check if all required fields are present
        if not all(
            key in filtered_data and filtered_data[key] is not None
            for key in ["id", "submitted_at", "account", "otp"]
        ):
            logging.warning("Missing required field(s) in questionnaire response")
            return None, Response(
                {"error": "Missing required field(s) in questionnaire response"},
                status=400,
            )

        return filtered_data, None

    return None, Response(
        {"error": "No questionnaire submission found or submission invalid"},
        status=403,
    )


def validate_password_strength(password) -> tuple[bool, dict | None]:
    """Helper function to validate password complexity and strength.

    Returns: A tuple of (is_valid, error_response).
    `is_valid` is True if the password is valid, otherwise False.
    `error_response` is a dict with a detailed error message if invalid, otherwise None.
    """
    # Quick length check first
    if len(password) < PASSWORD_LENGTH_MIN:
        return False, {
            "error": f"Password must be equal to or more than {PASSWORD_LENGTH_MIN} characters long.",
        }

    # Single regex pattern to check all character requirements at once
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).*$"
    if not re.match(pattern, password):
        return False, {
            "error": "Password must contain at least one uppercase letter, one lowercase letter, and one numeric digit.",
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
