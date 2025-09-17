import asyncio
import base64
import hashlib
import json
import logging
import secrets
import time

import dateutil.parser
import httpx
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django_redis import get_redis_connection
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.auth import utils
from apps.web.models import Student


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


LIMITS = {
    "courses": 20,
    "reviews": 5,
    "unauthenticated_review_search": 3,
}

OTP_TIME_OUT = settings.AUTH["OTP_TIME_OUT"]
TEMP_TOKEN_TIMEOUT = settings.AUTH["TEMP_TOKEN_TIMEOUT"]
ACTION_LIST = settings.AUTH["ACTION_LIST"]
TOKEN_RATE_LIMIT = settings.AUTH["TOKEN_RATE_LIMIT"]
TOKEN_RATE_LIMIT_TIME = settings.AUTH["TOKEN_RATE_LIMIT_TIME"]


@api_view(["POST"])
def auth_initiate_api(request):
    """Step 1: Authentication Initiation (/api/auth/initiate)

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
        return Response({"error": "Missing action or turnstile_token"}, status=400)

    if action not in ACTION_LIST:
        return Response({"error": "Invalid action"}, status=400)

    # Get client IP from trusted headers for enhanced Turnstile security
    client_ip = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )

    # Verify Turnstile token
    async def verify_turnstile():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": turnstile_token,
                    "remoteip": client_ip,
                },
            )
            return response.json()

    # Verify Turnstile token
    try:
        result = asyncio.run(verify_turnstile())
        if not result.get("success"):
            logging.warning(f"Turnstile verification failed: {result}")
            return Response({"error": "Turnstile verification failed"}, status=403)
    except Exception as e:
        logging.error(f"Error verifying Turnstile token: {e}")
        return Response({"error": "Turnstile verification error"}, status=500)

    # Generate cryptographically secure OTP and temp_token
    otp_bytes = secrets.token_bytes(6)
    otp = base64.b64encode(otp_bytes).decode("ascii")[:8]  # 8-digit OTP

    temp_token = secrets.token_urlsafe(32)  # 256-bit temp_token

    # Create Redis storage
    r = get_redis_connection("default")

    # Clean up any existing temp_token for this client to prevent memory leaks
    existing_temp_token = request.COOKIES.get("temp_token")
    if existing_temp_token:
        try:
            existing_hash = hashlib.sha256(existing_temp_token.encode()).hexdigest()
            existing_state_key = f"temp_token_state:{existing_hash}"
            existing_state_data = r.get(existing_state_key)
            if existing_state_data:
                # Clean up existing state and any associated OTP
                existing_state = json.loads(existing_state_data)
                r.delete(existing_state_key)
                logging.info(
                    f"Cleaned up existing temp_token_state for action {existing_state.get('action', 'unknown')}",
                )
        except Exception as e:
            logging.warning(f"Error cleaning up existing temp_token: {e}")

    # Store OTP -> temp_token mapping with initiated_at timestamp
    current_time = time.time()
    otp_data = {"temp_token": temp_token, "initiated_at": current_time}
    r.setex(f"otp:{otp}", OTP_TIME_OUT, json.dumps(otp_data))

    # Store temp_token with SHA256 hash as key, and status of pending as well as action
    temp_token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
    temp_token_state = {"status": "pending", "action": action}
    r.setex(
        f"temp_token_state:{temp_token_hash}",
        TEMP_TOKEN_TIMEOUT,
        json.dumps(temp_token_state),
    )

    logging.info(f"Created auth intent for action {action} with OTP and temp_token")

    survey_url = utils.get_survey_url(action)

    if not survey_url:
        return Response(
            {"error": "Something went wrong when fetching the survey URL"},
            status=500,
        )

    # Create response and set temp_token as HttpOnly cookie
    response = Response({"otp": otp, "redirect_url": survey_url}, status=200)

    # Set temp_token as secure HttpOnly cookie
    response.set_cookie(
        "temp_token",
        temp_token,
        max_age=TEMP_TOKEN_TIMEOUT,
        httponly=True,
        secure=getattr(settings, "SECURE_COOKIES", True),
    )

    return response


@api_view(["POST"])
def verify_callback_api(request):
    """Callback Verification (/api/auth/verify)
    request data includes account, answer_id, action
    Handles the verification of questionnaire callback using temp_token from cookie.
    """
    # Get required parameters from request
    account = request.data.get("account")
    answer_id = request.data.get("answer_id")
    action = request.data.get("action")

    if not account or not answer_id or not action:
        return Response({"error": "Missing account, answer_id, or action"}, status=400)

    # Get temp_token from HttpOnly cookie
    temp_token = request.COOKIES.get("temp_token")
    if not temp_token:
        return Response({"error": "No temp_token found"}, status=401)

    r = get_redis_connection("default")

    # Step 1: Look up temp_token state record
    temp_token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
    state_key = f"temp_token_state:{temp_token_hash}"
    state_data = r.get(state_key)

    if not state_data:
        return Response({"error": "Temp token state not found or expired"}, status=401)

    try:
        state_data = json.loads(state_data)
    except json.JSONDecodeError:
        return Response({"error": "Invalid temp token state data"}, status=401)

    # Verify status is pending and action matches
    if state_data.get("status") != "pending":
        return Response({"error": "Invalid temp token state"}, status=401)

    if state_data.get("action") != action:
        return Response({"error": "Action mismatch"}, status=403)

    # Step 2: Apply rate limiting per temp_token to prevent brute-force attempts
    rate_limit_key = (
        f"verify_attempts:{hashlib.sha256(temp_token.encode()).hexdigest()}"
    )

    attempts = r.incr(rate_limit_key)

    if attempts == 1:
        r.expire(rate_limit_key, TOKEN_RATE_LIMIT_TIME)

    if attempts > TOKEN_RATE_LIMIT:
        return Response({"error": "Too many verification attempts"}, status=429)

    # Step 3: Query questionnaire API for latest submission of the specific questionnaire of the action
    latest_answer, error_response = asyncio.run(
        utils.get_latest_answer(action=action, account=account),
    )
    if error_response:
        return error_response

    # Check if this is the submission we're looking for
    if str(latest_answer.get("id")) != str(answer_id):
        return Response({"error": "Answer ID mismatch"}, status=403)

    # Extract OTP and quest_id from submission
    submitted_otp = latest_answer.get("verification_code")

    # Atomically get and delete OTP record to prevent reuse
    otp_key = f"otp:{submitted_otp}"
    otp_data_raw = r.getdel(otp_key)

    if not otp_data_raw:
        return Response({"error": "Invalid or expired OTP"}, status=401)

    try:
        otp_data = json.loads(otp_data_raw.decode("utf-8"))
        expected_temp_token = otp_data.get("temp_token")
        initiated_at = otp_data.get("initiated_at")
    except (json.JSONDecodeError, AttributeError):
        return Response({"error": "Invalid OTP data format"}, status=401)

    if not expected_temp_token or not initiated_at:
        return Response({"error": "Incomplete OTP data"}, status=401)

    # Step 5: StepVerify temp_token matches
    if expected_temp_token != temp_token:
        return Response({"error": "Invalid temp_token"}, status=401)

    # Step 6: Validate submission timestamp after OTP extraction
    try:
        submitted_at_str = latest_answer.get("submitted_at")

        submitted_at = dateutil.parser.parse(submitted_at_str).timestamp()

        # Additional validation: check submission is after initiation and within window
        if submitted_at < initiated_at or (submitted_at - initiated_at) > OTP_TIME_OUT:
            return Response(
                {"error": "Submission timestamp outside validity window"},
                status=401,
            )

    except (ValueError, TypeError) as e:
        logging.exception(f"Error parsing submission timestamp: {e}")
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

    logging.info(
        f"Successfully verified temp_token for user {account} with action {action}",
    )

    # For login action, handle immediate session creation and cleanup
    is_logged_in = False
    if action == "login":
        user, error_response = utils.create_user_session(request, account)
        if user is None or error_response:
            logging.error(
                f"Failed to create session for login: {error_response.data['error']}",
            )
            return error_response
        if not user.is_active:
            logging.warning(f"Inactive user attempted OAuth login: {account}")
            return Response({"error": "User account is inactive"}, status=403)
        try:
            # Create Django session
            login(request, user)
            is_logged_in = True
            # Delete temp_token_state after successful login
            r.delete(state_key)
        except Exception as e:
            logging.exception(
                f"Error during login session creation or cleanup for user {account}: {e}",
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


def verify_psd_checker(request, action: str) -> tuple[dict | None, Response | None]:
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
def auth_signup_api(request) -> Response:
    """Signup API (/api/auth/signup)

    Handles user signup using verified temp_token.
    """
    try:
        verification_data, error_response = verify_psd_checker(request, action="signup")
        if verification_data is None or error_response:
            return error_response

        account = verification_data.get("account")
        password = verification_data.get("password")
        state_key = verification_data.get("state_key")

        # Create user session
        user, error_response = utils.create_user_session(request, account)
        if user is None or error_response:
            return error_response
        if user.password:
            return Response({"error": "User already exists with password."}, status=409)

        user.is_active = True
        # Set password
        user.set_password(password)
        user.save()

        # Cleanup: Delete temp_token_state and clear cookie
        r = get_redis_connection("default")
        r.delete(state_key)
        response = Response({"success": True, "username": user.username}, status=200)
        response.delete_cookie("temp_token")
        return response

    except Exception as e:
        logging.error(f"Error in auth_signup_api: {e}")
        return Response({"error": "Failed to complete signup"}, status=500)


@api_view(["POST"])
def auth_reset_password_api(request) -> Response:
    """Reset Password API (/api/auth/password)

    Handles password reset using verified temp_token.
    """
    try:
        verification_data, error_response = verify_psd_checker(
            request,
            action="reset_password",
        )
        if verification_data is None or error_response:
            return error_response
        account = verification_data.get("account")
        password = verification_data.get("password")
        state_key = verification_data.get("state_key")

        # Get the user object and update password
        User = get_user_model()
        try:
            user = User.objects.get(username=account)
            user.set_password(password)
            user.save()
        except User.DoesNotExist:
            return Response({"error": "User does not exist"}, status=404)

        # Cleanup: Delete temp_token_state and clear cookie
        r = get_redis_connection("default")
        r.delete(state_key)
        response = Response({"success": True, "username": user.username}, status=200)
        response.delete_cookie("temp_token")
        return response

    except Exception as e:
        logging.error(f"Error in auth_reset_password_api: {e}")
        return Response({"error": "Failed to reset password"}, status=500)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def auth_login_api(request) -> Response:
    email = request.data.get("email", "").lower()
    password = request.data.get("password", "")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)

    username = email.split("@")[0]
    user = authenticate(username=username, password=password)

    if user is not None:
        if user.is_active:
            login(request, user)
            # Link user to a student profile
            Student.objects.get_or_create(user=user)
            request.session["user_id"] = user.username

            return Response({"success": True, "username": user.username})
        return Response(
            {
                "error": "Please activate your account via the activation link first.",
            },
            status=403,
        )
    return Response({"error": "Invalid email or password"}, status=401)


@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def auth_logout_api(request) -> Response:
    """Logout a user."""
    logout(request)
    return Response({"message": "Logged out successfully"}, status=200)
