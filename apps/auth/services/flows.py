import asyncio
import json
import logging
import time

import dateutil.parser

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login

from apps.auth.services.captcha import verify_turnstile_token
from apps.auth.services.passwords import validate_password_strength
from apps.auth.services.questionnaire import get_latest_answer, get_survey_details
from apps.auth.services.tokens import (
    OTP_TIMEOUT,
    TEMP_TOKEN_TIMEOUT,
    cleanup_existing_temp_token,
    generate_otp,
    generate_temp_token,
    get_auth_redis,
    get_client_ip,
    get_state_key,
    get_token_hash,
    store_auth_intent,
)
from apps.auth.services.types import (
    AuthIntent,
    CallbackVerification,
    PasswordVerification,
    ServiceError,
)
from apps.auth.services.users import create_user_session
from apps.web.models import Student

logger = logging.getLogger(__name__)

AUTH_SETTINGS = settings.AUTH
ACTION_LIST = AUTH_SETTINGS["ACTION_LIST"]
TOKEN_RATE_LIMIT = AUTH_SETTINGS["TOKEN_RATE_LIMIT"]
TOKEN_RATE_LIMIT_TIME = AUTH_SETTINGS["TOKEN_RATE_LIMIT_TIME"]


def initiate_auth(request) -> tuple[AuthIntent | None, ServiceError | None]:
    # Get required fields from request data
    action = request.data.get("action")
    turnstile_token = request.data.get("turnstile_token")

    if not action or not turnstile_token:
        logger.warning("Missing action or turnstile_token in auth_initiate_api")

        return None, ServiceError(
            "Missing action or turnstile_token",
            status=400,
        )

    if action not in ACTION_LIST:
        logger.warning("Invalid action '%s' in auth_initiate_api", action)

        return None, ServiceError("Invalid action", status=400)

    client_ip = get_client_ip(request)

    # Verify Turnstile token
    success, error = asyncio.run(
        verify_turnstile_token(turnstile_token, client_ip),
    )
    if not success:
        logger.warning(
            "verify_turnstile_token failed in auth_initiate_api:%s",
            error.as_payload() if error else None,
        )

        return None, error or ServiceError(
            "Turnstile verification failed",
            status=502,
        )

    details = get_survey_details(action)
    if not details:
        logger.error("Invalid action '%s' when fetching survey details", action)

        return None, ServiceError("Invalid action", status=400)

    survey_url = details.get("url")
    if not survey_url:
        logger.error("Survey URL missing for %s", action)

        return None, ServiceError(
            "Something went wrong when fetching the survey URL",
            status=500,
        )

    # Generate cryptographically secure OTP and temp_token
    otp = generate_otp()
    temp_token = generate_temp_token()

    # Create Redis storage and clean up existing tokens
    try:
        redis_client = get_auth_redis()
        cleanup_existing_temp_token(redis_client, request.COOKIES.get("temp_token"))
        store_auth_intent(redis_client, otp, temp_token, action)
    except Exception:
        logger.exception("Failed to create auth intent")

        return None, ServiceError(
            "Failed to create auth intent",
            status=500,
        )

    logger.info("Created auth intent for action %s with OTP and temp_token", action)

    return AuthIntent(
        otp=otp,
        temp_token=temp_token,
        redirect_url=survey_url,
    ), None


def _load_pending_temp_token_state(
    redis_client,
    temp_token: str,
    action: str,
) -> tuple[str | None, dict | None, ServiceError | None]:
    # Step 1: Look up temp_token state record
    state_key = get_state_key(temp_token)
    state_data_raw = redis_client.get(state_key)

    if not state_data_raw:
        logger.warning("Temp token state not found or expired in verify_callback_api")

        return (
            None,
            None,
            ServiceError(
                "Temp token state not found or expired",
                status=401,
            ),
        )

    try:
        state_data = json.loads(state_data_raw)
    except json.JSONDecodeError:
        logger.error("Invalid temp token state data in verify_callback_api")

        return (
            None,
            None,
            ServiceError(
                "Invalid temp token state data",
                status=401,
            ),
        )

    if not isinstance(state_data, dict):
        logger.error("Invalid temp token state data in verify_callback_api")

        return (
            None,
            None,
            ServiceError(
                "Invalid temp token state data",
                status=401,
            ),
        )

    # Verify status is pending and action matches
    if state_data.get("status") != "pending":
        logger.warning("Temp token state not pending in verify_callback_api")

        return (
            None,
            None,
            ServiceError(
                "Invalid temp token state",
                status=401,
            ),
        )

    if state_data.get("action") != action:
        logger.warning("Action mismatch in verify_callback_api")

        return None, None, ServiceError("Action mismatch", status=403)

    return state_key, state_data, None


def _apply_verification_rate_limit(
    redis_client,
    temp_token: str,
) -> tuple[str | None, ServiceError | None]:
    # Step 2: Apply rate limiting per temp_token to prevent brute-force attempts
    rate_limit_key = f"verify_attempts:{get_token_hash(temp_token)}"

    attempts = redis_client.incr(rate_limit_key)

    if attempts == 1:
        redis_client.expire(rate_limit_key, TOKEN_RATE_LIMIT_TIME)

    if attempts > TOKEN_RATE_LIMIT:
        logger.warning("Too many verification attempts in verify_callback_api")

        return None, ServiceError(
            "Too many verification attempts",
            status=429,
        )

    return rate_limit_key, None


def _get_and_validate_latest_answer(
    action: str,
    account: str,
    answer_id,
) -> tuple[dict | None, ServiceError | None]:
    # Step 3: Query questionnaire API for latest submission of the specific questionnaire of the action
    latest_answer, error = asyncio.run(
        get_latest_answer(action=action, account=account),
    )
    if error:
        return None, error

    if latest_answer is None:
        logger.warning("No questionnaire submission found in verify_callback_api")

        return None, ServiceError(
            "No questionnaire submission found",
            status=404,
        )

    # Check if this is the submission we're looking for
    if str(latest_answer.get("id")) != str(answer_id):
        logger.warning("Answer ID mismatch in verify_callback_api")

        return None, ServiceError("Answer ID mismatch", status=403)

    return latest_answer, None


def _consume_and_validate_otp(
    redis_client,
    submitted_otp,
    temp_token: str,
) -> tuple[float | None, ServiceError | None]:
    # Atomically get and delete OTP record to prevent reuse
    otp_key = f"otp:{submitted_otp}"
    otp_data_raw = redis_client.getdel(otp_key)

    if not otp_data_raw:
        logger.warning("Invalid or expired OTP in verify_callback_api")

        return None, ServiceError(
            "Invalid or expired OTP",
            status=401,
        )

    try:
        otp_data = json.loads(otp_data_raw.decode("utf-8"))
        expected_temp_token = otp_data.get("temp_token")
        initiated_at = otp_data.get("initiated_at")
    except json.JSONDecodeError, AttributeError, TypeError:
        logger.error("Invalid OTP data format in verify_callback_api")

        return None, ServiceError(
            "Invalid OTP data format",
            status=401,
        )

    if not expected_temp_token or not initiated_at:
        logger.warning("Incomplete OTP data in verify_callback_api")

        return None, ServiceError(
            "Incomplete OTP data",
            status=401,
        )

    # Step 5: StepVerify temp_token matches
    if expected_temp_token != temp_token:
        logger.warning("Invalid temp_token in verify_callback_api")

        return None, ServiceError(
            "Invalid temp_token",
            status=401,
        )

    return float(initiated_at), None


def _validate_submission_timestamp(
    latest_answer: dict,
    initiated_at: float,
) -> ServiceError | None:
    # Step 6: Validate submission timestamp after OTP extraction
    try:
        submitted_at_str = latest_answer.get("submitted_at")
        if submitted_at_str is None:
            return ServiceError(
                "Missing submission timestamp",
                status=400,
            )

        submitted_at = dateutil.parser.parse(submitted_at_str).timestamp()

        # Additional validation: check submission is after initiation and within window
        if submitted_at < initiated_at or (submitted_at - initiated_at) > OTP_TIMEOUT:
            return ServiceError(
                "Submission timestamp outside validity window",
                status=401,
            )

    except ValueError, TypeError:
        logger.error("Error parsing submission timestamp")

        return ServiceError(
            "Invalid submission timestamp",
            status=401,
        )

    return None


def _mark_temp_token_verified(
    redis_client,
    state_key: str,
    state_data: dict,
    account: str,
) -> int:
    # Step 7: Update state to verified and add user details
    state_data.update(
        {
            "status": "verified",
            "account": account,
        },
    )

    # Update temp_token_state in Redis with refreshed TTL
    redis_client.setex(state_key, TEMP_TOKEN_TIMEOUT, json.dumps(state_data))

    return int(time.time() + TEMP_TOKEN_TIMEOUT)


def _login_verified_user(
    request,
    redis_client,
    state_key: str,
    account: str,
) -> tuple[bool, ServiceError | None]:
    user, error = create_user_session(request, account)
    if user is None:
        if error:
            logger.error(
                "Failed to create session for login: %s",
                error.as_payload().get("error", "Unknown error"),
            )

            return False, error

        logger.error("Failed to create user session in verify_callback_api")

        return False, ServiceError(
            "Failed to create user session",
            status=500,
        )

    if not user.is_active:
        logger.warning("Inactive user attempted OAuth login: %s", account)

        return False, ServiceError(
            "User account is inactive",
            status=403,
        )

    try:
        # Create Django session
        login(request, user)

        # Delete temp_token_state after successful login
        redis_client.delete(state_key)
    except Exception:
        logger.exception(
            "Error during login session creation or cleanup for user %s",
            account,
        )

        return False, ServiceError(
            "Failed to finalize login process",
            status=500,
        )

    return True, None


def verify_callback(request) -> tuple[CallbackVerification | None, ServiceError | None]:
    logger.info(
        "verify_callback_api called for account=%s, action=%s",
        request.data.get("account"),
        request.data.get("action"),
    )

    # Get required parameters from request
    account = request.data.get("account")
    answer_id = request.data.get("answer_id")
    action = request.data.get("action")

    if not account or not answer_id or not action:
        logger.warning("Missing account, answer_id, or action in verify_callback_api")

        return None, ServiceError(
            "Missing account, answer_id, or action",
            status=400,
        )

    if action not in ACTION_LIST:
        logger.warning("Invalid action '%s' in verify_callback_api", action)

        return None, ServiceError("Invalid action", status=400)

    # Get temp_token from HttpOnly cookie
    temp_token = request.COOKIES.get("temp_token")
    if not temp_token:
        logger.warning("No temp_token found in verify_callback_api")

        return None, ServiceError("No temp_token found", status=401)

    redis_client = get_auth_redis()

    state_key, state_data, error = _load_pending_temp_token_state(
        redis_client,
        temp_token,
        action,
    )
    if error:
        return None, error

    rate_limit_key, error = _apply_verification_rate_limit(redis_client, temp_token)
    if error:
        return None, error

    latest_answer, error = _get_and_validate_latest_answer(
        action,
        account,
        answer_id,
    )
    if error:
        return None, error

    # Extract OTP and quest_id from submission
    submitted_otp = latest_answer.get("otp")

    initiated_at, error = _consume_and_validate_otp(
        redis_client,
        submitted_otp,
        temp_token,
    )
    if error:
        return None, error

    error = _validate_submission_timestamp(latest_answer, initiated_at)
    if error:
        return None, error

    expires_at = _mark_temp_token_verified(
        redis_client,
        state_key,
        state_data,
        account,
    )

    # Clear rate limiting on success
    redis_client.delete(rate_limit_key)

    logger.info(
        "Successfully verified temp_token for user %s with action %s",
        account,
        action,
    )

    # For login action, handle immediate session creation and cleanup
    is_logged_in = False
    if action == "login":
        is_logged_in, error = _login_verified_user(
            request,
            redis_client,
            state_key,
            account,
        )
        if error:
            return None, error

    return CallbackVerification(
        action=action,
        expires_at=expires_at,
        is_logged_in=is_logged_in,
    ), None


def verify_token_pwd(
    request,
    action: str,
) -> tuple[PasswordVerification | None, ServiceError | None]:
    # Get temp_token from HttpOnly cookie
    temp_token = request.COOKIES.get("temp_token")
    if not temp_token:
        return None, ServiceError("No temp_token found", status=401)

    redis_client = get_auth_redis()

    # Look up temp_token state record
    state_key = get_state_key(temp_token)
    state_data_raw = redis_client.get(state_key)

    if not state_data_raw:
        return None, ServiceError(
            "Temp token state not found or expired",
            status=401,
        )

    try:
        state_data = json.loads(state_data_raw)
    except json.JSONDecodeError:
        return None, ServiceError(
            "Invalid temp token state data",
            status=401,
        )

    if not isinstance(state_data, dict):
        return None, ServiceError(
            "Invalid temp token state data",
            status=401,
        )

    # Verify status is verified and action is signup
    if state_data.get("status") != "verified" or state_data.get("action") != action:
        return None, ServiceError(
            "Invalid temp token state",
            status=403,
        )

    # Get password from request data
    password = request.data.get("password")
    if not password:
        return None, ServiceError("Missing password", status=400)

    # Validate password strength
    is_valid, password_error = validate_password_strength(password)
    if not is_valid:
        return None, ServiceError(
            "Invalid password",
            status=400,
            payload=password_error,
        )

    # Get account from verified state
    account = state_data.get("account")
    if not account:
        return None, ServiceError(
            "No account in verified state",
            status=401,
        )

    return PasswordVerification(
        account=account,
        password=password,
        state_key=state_key,
    ), None


def complete_signup(request) -> tuple[dict | None, ServiceError | None]:
    try:
        verification_data, error = verify_token_pwd(request, action="signup")
        if verification_data is None:
            return None, error or ServiceError("Verification failed", status=400)

        # Create user session
        user, error = create_user_session(request, verification_data.account)
        if user is None:
            return None, error or ServiceError(
                "Failed to create user session",
                status=500,
            )

        if user.password:
            return None, ServiceError(
                "User already exists with password.",
                status=409,
            )

        user.is_active = True

        # Set password
        user.set_password(verification_data.password)
        user.save()

        login(request, user)

        # Cleanup: Delete temp_token_state and clear cookie
        redis_client = get_auth_redis()
        redis_client.delete(verification_data.state_key)

        return {"success": True, "username": user.username}, None

    except Exception:
        logger.exception("Error in auth_signup_api")

        return None, ServiceError(
            "Failed to complete signup",
            status=500,
        )


def reset_password(request) -> tuple[dict | None, ServiceError | None]:
    try:
        verification_data, error = verify_token_pwd(
            request,
            action="reset_password",
        )
        if verification_data is None:
            return None, error or ServiceError("Verification failed", status=400)

        # Get the user object and update password
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=verification_data.account)
            user.set_password(verification_data.password)
            user.save()
        except user_model.DoesNotExist:
            return None, ServiceError(
                "User does not exist",
                status=404,
            )

        # Cleanup: Delete temp_token_state and clear cookie
        redis_client = get_auth_redis()
        redis_client.delete(verification_data.state_key)

        return {"success": True, "username": user.username}, None

    except Exception:
        logger.exception("Error in auth_reset_password_api")

        return None, ServiceError(
            "Failed to reset password",
            status=500,
        )


def login_with_password(request) -> tuple[dict | None, ServiceError | None]:
    account = request.data.get("account", "").strip()
    password = request.data.get("password", "")
    turnstile_token = request.data.get("turnstile_token", "")

    if not account or not password or not turnstile_token:
        logger.warning(
            "Account, password, and Turnstile token are missing in auth_login_api",
        )

        return None, ServiceError(
            "Account, password, and Turnstile token are missing",
            status=400,
        )

    client_ip = get_client_ip(request)

    success, error = asyncio.run(
        verify_turnstile_token(turnstile_token, client_ip),
    )
    if not success:
        return None, error or ServiceError(
            "Turnstile verification failed",
            status=502,
        )

    user = authenticate(request, username=account, password=password)
    if user is None or not user.is_active:
        return None, ServiceError(
            "Invalid account or password",
            status=401,
        )

    login(request, user)
    Student.objects.get_or_create(user=user)

    return {"message": "Login successfully"}, None
