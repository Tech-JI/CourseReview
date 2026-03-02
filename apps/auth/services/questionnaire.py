import json
import logging

from typing import Any

import httpx

from django.conf import settings

from apps.auth.services.types import ServiceError

logger = logging.getLogger(__name__)

AUTH_SETTINGS = settings.AUTH
OTP_TIMEOUT = AUTH_SETTINGS["OTP_TIMEOUT"]

QUEST_SETTINGS = settings.QUEST
QUEST_BASE_URL = QUEST_SETTINGS["BASE_URL"]


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
    except ValueError, TypeError:
        logger.error(
            "Could not parse 'QUESTIONID' for action '%s'. Check your settings.",
            action,
        )

        return None

    return {
        "url": action_details.get("URL"),
        "api_key": action_details.get("API_KEY"),
        "question_id": question_id,
    }


async def get_latest_answer(
    action: str,
    account: str,
) -> tuple[dict | None, ServiceError | None]:
    """Fetch the latest questionnaire answer for a given account from the WJ API(specific api for actions)."""

    details = get_survey_details(action)
    if not details:
        return None, ServiceError("Invalid action", status=400)

    quest_api = details.get("api_key")
    if not quest_api:
        return None, ServiceError("Invalid action", status=400)

    # Get the target question ID for the verification code
    question_id = details.get("question_id")
    if not question_id:
        return None, ServiceError(
            "Configuration error: question ID not found for action",
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

    except httpx.TimeoutException:
        logger.error("Questionnaire API query timed out")

        return None, ServiceError(
            "Questionnaire API query timed out",
            status=504,
        )

    except httpx.RequestError, httpx.HTTPStatusError:
        logger.error("Error querying questionnaire API")

        return None, ServiceError(
            "Failed to query questionnaire API",
            status=500,
        )

    except Exception:
        logger.exception("An unexpected error occurred")

        return None, ServiceError(
            "An unexpected error occurred",
            status=500,
        )

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
        }

        # Check if all required fields are present
        if not all(
            key in filtered_data and filtered_data[key] is not None
            for key in ["id", "submitted_at", "account", "otp"]
        ):
            logger.warning("Missing required field(s) in questionnaire response")

            return None, ServiceError(
                "Missing required field(s) in questionnaire response",
                status=400,
            )

        return filtered_data, None

    return None, ServiceError(
        "No questionnaire submission found or submission invalid",
        status=403,
    )
