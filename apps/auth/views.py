import asyncio
import hashlib
import json
import logging
import secrets
import time

import dateutil.parser
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django_redis import get_redis_connection
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.auth import utils
from apps.web.models import Student

logger = logging.getLogger(__name__)


AUTH_SETTINGS = settings.AUTH
OTP_TIMEOUT = AUTH_SETTINGS["OTP_TIMEOUT"]
TEMP_TOKEN_TIMEOUT = AUTH_SETTINGS["TEMP_TOKEN_TIMEOUT"]
ACTION_LIST = AUTH_SETTINGS["ACTION_LIST"]
TOKEN_RATE_LIMIT = AUTH_SETTINGS["TOKEN_RATE_LIMIT"]
TOKEN_RATE_LIMIT_TIME = AUTH_SETTINGS["TOKEN_RATE_LIMIT_TIME"]


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_initiate_api(request):
    """Step 1: Authentication Initiation (/api/auth/init)

    1. Receives action and turnstile_token from frontend
    2. Verifies Turnstile token with Cloudflare's API
    3. Generates cryptographically secure OTP and temp_token
    4. Stores OTP->temp_token mapping and temp_token state in Redis
    5. Sets temp_token as HttpOnly cookie and returns OTP and redirect_url
    """
    # Get required fields from request data
    action = request.data.get("action")
    turnstile_token = request.data.get("turnstile_token")

    if not action or not turnstile_token:
        logger.warning("Missing action or turnstile_token in auth_initiate_api")
        return Response({"error": "Missing action or turnstile_token"}, status=400)

    if action not in ACTION_LIST:
        logger.warning("Invalid action '%s' in auth_initiate_api", action)
        return Response({"error": "Invalid action"}, status=400)

    client_ip = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )

    # Verify Turnstile token
    success, error_response = asyncio.run(
        utils.verify_turnstile_token(turnstile_token, client_ip)
    )
    if not success:
        logger.warning(
            "verify_turnstile_token failed in auth_initiate_api:%s",
            error_response.data,
        )
        return error_response

    # Generate cryptographically secure OTP and temp_token
    otp = "".join([str(secrets.randbelow(10)) for _ in range(8)])
    temp_token = secrets.token_urlsafe(32)

    # Create Redis storage and clean up existing tokens
    r = get_redis_connection("default")

    # Clean up any existing temp_token for this client to prevent memory leaks
    existing_temp_token = request.COOKIES.get("temp_token")
    if existing_temp_token:
        try:
            existing_hash = hashlib.sha256(existing_temp_token.encode()).hexdigest()
            existing_state_key = f"temp_token_state:{existing_hash}"
            existing_state_data = r.get(existing_state_key)
            if existing_state_data:
                existing_state = json.loads(existing_state_data)
                r.delete(existing_state_key)
                logger.info(
                    "Cleaned up existing temp_token_state for action %s",
                    existing_state.get("action", "unknown"),
                )
        except Exception:
            logger.warning("Error cleaning up existing temp_token")

    # Store OTP -> temp_token mapping with initiated_at timestamp
    current_time = time.time()
    otp_data = {"temp_token": temp_token, "initiated_at": current_time}
    r.setex(f"otp:{otp}", OTP_TIMEOUT, json.dumps(otp_data))

    # Store temp_token with SHA256 hash as key, and status of pending as well as action
    temp_token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
    temp_token_state = {"status": "pending", "action": action}
    r.setex(
        f"temp_token_state:{temp_token_hash}",
        TEMP_TOKEN_TIMEOUT,
        json.dumps(temp_token_state),
    )

    logger.info("Created auth intent for action %s with OTP and temp_token", action)

    details = utils.get_survey_details(action)
    if not details:
        logger.error("Invalid action '%s' when fetching survey details", action)
        return Response({"error": "Invalid action"}, status=400)
    survey_url = details.get("url")
    if not survey_url:
        logger.error("Survey URL missing for %s", action)
        return Response(
            {"error": "Something went wrong when fetching the survey URL"},
            status=500,
        )

    # Create response and set temp_token as HttpOnly cookie
    response = Response({"otp": otp, "redirect_url": survey_url}, status=200)
    response.set_cookie(
        "temp_token",
        temp_token,
        max_age=TEMP_TOKEN_TIMEOUT,
        httponly=True,
        secure=getattr(settings, "SECURE_COOKIES", True),
        samesite="Lax",
    )
    return response


@ensure_csrf_cookie
@api_view(["POST"])
@permission_classes([AllowAny])
def verify_callback_api(request):
    """Callback Verification (/api/auth/verify)
    request data includes account, answer_id, action
    Handles the verification of questionnaire callback using temp_token from cookie.
    """
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
        return Response({"error": "Missing account, answer_id, or action"}, status=400)

    if action not in ACTION_LIST:
        logger.warning("Invalid action '%s' in verify_callback_api", action)
        return Response({"error": "Invalid action"}, status=400)

    # Get temp_token from HttpOnly cookie
    temp_token = request.COOKIES.get("temp_token")
    if not temp_token:
        logger.warning("No temp_token found in verify_callback_api")
        return Response({"error": "No temp_token found"}, status=401)

    r = get_redis_connection("default")

    # Step 1: Look up temp_token state record
    temp_token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
    state_key = f"temp_token_state:{temp_token_hash}"
    state_data = r.get(state_key)

    if not state_data:
        logger.warning("Temp token state not found or expired in verify_callback_api")
        return Response({"error": "Temp token state not found or expired"}, status=401)

    try:
        state_data = json.loads(state_data)
    except json.JSONDecodeError:
        logger.error("Invalid temp token state data in verify_callback_api")
        return Response({"error": "Invalid temp token state data"}, status=401)

    # Verify status is pending and action matches
    if state_data.get("status") != "pending":
        logger.warning("Temp token state not pending in verify_callback_api")
        return Response({"error": "Invalid temp token state"}, status=401)

    if state_data.get("action") != action:
        logger.warning("Action mismatch in verify_callback_api")
        return Response({"error": "Action mismatch"}, status=403)

    # Step 2: Apply rate limiting per temp_token to prevent brute-force attempts
    rate_limit_key = (
        f"verify_attempts:{hashlib.sha256(temp_token.encode()).hexdigest()}"
    )

    attempts = r.incr(rate_limit_key)

    if attempts == 1:
        r.expire(rate_limit_key, TOKEN_RATE_LIMIT_TIME)

    if attempts > TOKEN_RATE_LIMIT:
        logger.warning("Too many verification attempts in verify_callback_api")
        return Response({"error": "Too many verification attempts"}, status=429)

    # Step 3: Query questionnaire API for latest submission of the specific questionnaire of the action
    latest_answer, error_response = asyncio.run(
        utils.get_latest_answer(action=action, account=account),
    )
    if error_response:
        return error_response

    if latest_answer is None:
        logger.warning("No questionnaire submission found in verify_callback_api")
        return Response({"error": "No questionnaire submission found"}, status=404)

    # Check if this is the submission we're looking for
    if str(latest_answer.get("id")) != str(answer_id):
        logger.warning("Answer ID mismatch in verify_callback_api")
        return Response({"error": "Answer ID mismatch"}, status=403)

    # Extract OTP and quest_id from submission
    submitted_otp = latest_answer.get("otp")

    # Atomically get and delete OTP record to prevent reuse
    otp_key = f"otp:{submitted_otp}"
    otp_data_raw = r.getdel(otp_key)

    if not otp_data_raw:
        logger.warning("Invalid or expired OTP in verify_callback_api")
        return Response({"error": "Invalid or expired OTP"}, status=401)

    try:
        otp_data = json.loads(otp_data_raw.decode("utf-8"))
        expected_temp_token = otp_data.get("temp_token")
        initiated_at = otp_data.get("initiated_at")
    except (json.JSONDecodeError, AttributeError):
        logger.error("Invalid OTP data format in verify_callback_api")
        return Response({"error": "Invalid OTP data format"}, status=401)

    if not expected_temp_token or not initiated_at:
        logger.warning("Incomplete OTP data in verify_callback_api")
        return Response({"error": "Incomplete OTP data"}, status=401)

    # Step 5: StepVerify temp_token matches
    if expected_temp_token != temp_token:
        logger.warning("Invalid temp_token in verify_callback_api")
        return Response({"error": "Invalid temp_token"}, status=401)

    # Step 6: Validate submission timestamp after OTP extraction
    try:
        submitted_at_str = latest_answer.get("submitted_at")
        if submitted_at_str is None:
            return Response({"error": "Missing submission timestamp"}, status=400)

        submitted_at = dateutil.parser.parse(submitted_at_str).timestamp()

        # Additional validation: check submission is after initiation and within window
        if submitted_at < initiated_at or (submitted_at - initiated_at) > OTP_TIMEOUT:
            return Response(
                {"error": "Submission timestamp outside validity window"},
                status=401,
            )

    except (ValueError, TypeError):
        logger.error("Error parsing submission timestamp")
        return Response({"error": "Invalid submission timestamp"}, status=401)

    # Step 7: Update state to verified and add user details
    state_data.update(
        {
            "status": "verified",
            "account": account,
        },
    )

    # Update temp_token_state in Redis with refreshed TTL
    r.setex(state_key, TEMP_TOKEN_TIMEOUT, json.dumps(state_data))
    expires_at = int(time.time() + TEMP_TOKEN_TIMEOUT)

    # Clear rate limiting on success
    r.delete(rate_limit_key)

    logger.info(
        "Successfully verified temp_token for user %s with action %s",
        account,
        action,
    )

    # For login action, handle immediate session creation and cleanup
    is_logged_in = False
    if action == "login":
        user, error_response = utils.create_user_session(request, account)
        if user is None:
            if error_response:
                logger.error(
                    "Failed to create session for login: %s",
                    getattr(error_response, "data", {}).get("error", "Unknown error"),
                )
                return error_response
            else:
                logger.error("Failed to create user session in verify_callback_api")
                return Response({"error": "Failed to create user session"}, status=500)
        if not user.is_active:
            logger.warning("Inactive user attempted OAuth login: %s", account)
            return Response({"error": "User account is inactive"}, status=403)
        try:
            # Create Django session
            login(request, user)
            is_logged_in = True
            # Delete temp_token_state after successful login
            r.delete(state_key)
        except Exception:
            logger.exception(
                "Error during login session creation or cleanup for user %s", account
            )
            return Response({"error": "Failed to finalize login process"}, status=500)

    # Create response
    response = Response(
        {"action": action, "expires_at": expires_at, "is_logged_in": is_logged_in},
        status=200,
    )

    # Clear temp_token cookie if login succeeded
    if is_logged_in:
        response.delete_cookie("temp_token")

    return response


def verify_token_pwd(request, action: str) -> tuple[dict | None, Response | None]:
    # Get temp_token from HttpOnly cookie
    temp_token = request.COOKIES.get("temp_token")
    if not temp_token:
        return None, Response({"error": "No temp_token found"}, status=401)

    r = get_redis_connection("default")

    # Look up temp_token state record
    temp_token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
    state_key = f"temp_token_state:{temp_token_hash}"
    state_data = r.get(state_key)

    if not state_data:
        return None, Response(
            {"error": "Temp token state not found or expired"},
            status=401,
        )

    try:
        state_data = json.loads(state_data)
    except json.JSONDecodeError:
        return None, Response({"error": "Invalid temp token state data"}, status=401)

    # Verify status is verified and action is signup
    if state_data.get("status") != "verified" or state_data.get("action") != action:
        return None, Response({"error": "Invalid temp token state"}, status=403)

    # Get password from request data
    password = request.data.get("password")
    if not password:
        return None, Response({"error": "Missing password"}, status=400)

    # Validate password strength
    is_valid, error_response = utils.validate_password_strength(password)
    if not is_valid:
        return None, Response(error_response, status=400)
    # Get account from verified state
    account = state_data.get("account")
    if not account:
        return None, Response({"error": "No account in verified state"}, status=401)
    return {"account": account, "password": password, "state_key": state_key}, None


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
def auth_signup_api(request) -> Response:
    """Signup API (/api/auth/signup)

    Handles user signup using verified temp_token.
    """
    try:
        verification_data, error_response = verify_token_pwd(request, action="signup")
        if verification_data is None:
            return error_response or Response(
                {"error": "Verification failed"}, status=400
            )

        account = verification_data.get("account")
        password = verification_data.get("password")
        state_key = verification_data.get("state_key")

        # Create user session
        user, error_response = utils.create_user_session(request, account)
        if user is None:
            return error_response or Response(
                {"error": "Failed to create user session"}, status=500
            )
        if user.password:
            return Response({"error": "User already exists with password."}, status=409)

        user.is_active = True
        # Set password
        user.set_password(password)
        user.save()

        login(request, user)

        # Cleanup: Delete temp_token_state and clear cookie
        r = get_redis_connection("default")
        r.delete(state_key)
        response = Response({"success": True, "username": user.username}, status=200)
        response.delete_cookie("temp_token")
        return response

    except Exception:
        logger.error("Error in auth_signup_api")
        return Response({"error": "Failed to complete signup"}, status=500)


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
def auth_reset_password_api(request) -> Response:
    """Reset Password API (/api/auth/password)

    Handles password reset using verified temp_token.
    """
    try:
        verification_data, error_response = verify_token_pwd(
            request,
            action="reset",
        )
        if verification_data is None:
            return error_response or Response(
                {"error": "Verification failed"}, status=400
            )
        account = verification_data.get("account")
        password = verification_data.get("password")
        state_key = verification_data.get("state_key")

        # Get the user object and update password
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=account)
            user.set_password(password)
            user.save()
        except user_model.DoesNotExist:
            return Response({"error": "User does not exist"}, status=404)

        # Cleanup: Delete temp_token_state and clear cookie
        r = get_redis_connection("default")
        r.delete(state_key)
        response = Response({"success": True, "username": user.username}, status=200)
        response.delete_cookie("temp_token")
        return response

    except Exception:
        logger.error("Error in auth_reset_password_api")
        return Response({"error": "Failed to reset password"}, status=500)


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
@permission_classes([AllowAny])
def auth_login_api(request) -> Response:
    account = request.data.get("account", "").strip()
    password = request.data.get("password", "")
    turnstile_token = request.data.get("turnstile_token", "")

    if not account or not password or not turnstile_token:
        logger.warning(
            "Account, password, and Turnstile token are missing in auth_login_api"
        )
        return Response(
            {"error": "Account, password, and Turnstile token are missing"}, status=400
        )

    client_ip = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )

    success, error_response = asyncio.run(
        utils.verify_turnstile_token(turnstile_token, client_ip)
    )
    if not success:
        return error_response or Response(
            {"error": "Turnstile verification failed"}, status=502
        )

    user = authenticate(username=account, password=password)
    if user is None or not user.is_active:
        return Response({"error": "Invalid account or password"}, status=401)

    login(request, user)
    Student.objects.get_or_create(user=user)

    return Response({"message": "Login successfully"}, status=200)


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
@permission_classes([AllowAny])
def auth_logout_api(request) -> Response:
    logger.info(
        "auth_logout_api called for user=%s",
        getattr(request.user, "username", None),
    )
    """Logout a user."""
    logout(request)
    return Response({"message": "Logged out successfully"}, status=200)
