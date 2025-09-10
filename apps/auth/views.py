import json
import httpx
import asyncio
import logging
import time
import secrets
import base64
import dateutil.parser
import hashlib
import re
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django_redis import get_redis_connection
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.web.models import Student
from rest_framework.decorators import api_view
from rest_framework.response import Response

OTP_TIME_OUT = 120  # 2 min
TEMP_TOKEN_TIMEOUT = 600  # 10 min
ACTION_LIST = ["signup", "login", "reset_password"]
TOKEN_RATE_LIMIT = 5  # max 5 callback attempts per temp_token
TOKEN_RATE_LIMIT_TIME = 600  # 10 minutes window


def get_survey_url(action: str) -> str:
    """
    Helper function to get the survey URL based on action type
    """
    if action == "signup":
        return settings.SIGNUP_WJ_URL
    elif action == "login":
        return settings.LOGIN_WJ_URL
    elif action == "reset_password":
        return settings.RESET_WJ_URL
    else:
        return None


def get_survey_api_key(action: str) -> str:
    """
    Helper function to get the survey API key based on action type
    """
    if action == "signup":
        return settings.SIGNUP_WJ_API_KEY
    elif action == "login":
        return settings.LOGIN_WJ_API_KEY
    elif action == "reset_password":
        return settings.RESET_WJ_API_KEY
    else:
        return None


@api_view(["POST"])
def auth_initiate_api(request):
    """
    Step 1: Authentication Initiation (/api/auth/initiate)

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
                    f"Cleaned up existing temp_token_state for action {existing_state.get('action', 'unknown')}"
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

    survey_url = get_survey_url(action)

    if not survey_url:
        return Response(
            {"error": "Something went wrong when fetching the survey URL"}, status=500
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
        samesite="Strict",
    )

    return response


@api_view(["GET"])
def auth_config_api(request):
    """
    API endpoint to provide configuration for the frontend
    """
    return Response(
        {
            "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
            "SURVEY_URL": settings.SURVEY_URL,
        },
        status=200,
    )


async def get_latest_answer(action: str, account: str) -> dict:
    """
    Fetch the latest questionnaire answer for a given account from the WJ API(specific api for actions).
    Returns filtered data with only: id(the answer id), ip_address, submitted_at, user.account and verification_code from the row
    """
    wj_api = get_survey_api_key(action)
    if not wj_api:
        return None

    BASE_URL = "https://wj.sjtu.edu.cn/api/v1/public/export"

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
    full_url_path = f"{BASE_URL}/{wj_api}/json"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            full_url_path, params=final_query_params, timeout=OTP_TIME_OUT
        )
        full_data = response.json()

        # Filter and return only the required fields from the first row
        if (
            full_data.get("success")
            and full_data.get("data")
            and full_data["data"].get("rows")
            and len(full_data["data"]["rows"]) > 0
        ):
            latest_answer = full_data["data"]["rows"][0]  # Get the first (latest) row

            # Extract the 8-digit verification code from the first answer
            verification_code = None
            if (
                latest_answer.get("answers")
                and len(latest_answer["answers"]) > 0
                and latest_answer["answers"][0].get("answer")
            ):
                verification_code = latest_answer["answers"][0]["answer"]

            # Extract only the required fields from this row
            filtered_data = {
                "id": latest_answer.get("id"),
                "submitted_at": latest_answer.get("submitted_at"),
                "account": latest_answer.get("user", {}).get("account")
                if latest_answer.get("user")
                else None,
                "verification_code": verification_code,
            }

            # Check if all required fields are present
            if not all(filtered_data.values()):
                logging.warning(f"Missing required field(s) in questionnaire response")
                return None

            return filtered_data

        return None


@api_view(["POST"])
def verify_callback_api(request):
    """
    Callback Verification (/api/auth/verify)
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

    # Apply rate limiting per temp_token to prevent brute-force attempts
    rate_limit_key = (
        f"verify_attempts:{hashlib.sha256(temp_token.encode()).hexdigest()}"
    )

    attempts = r.incr(rate_limit_key)

    if attempts == 1:
        r.expire(rate_limit_key, TOKEN_RATE_LIMIT_TIME)

    if attempts > TOKEN_RATE_LIMIT:
        return Response({"error": "Too many verification attempts"}, status=429)

    # Step 1: Query questionnaire API for latest submission of the specific questionnaire of the action
    try:
        latest_answer = asyncio.run(get_latest_answer(action=action, account=account))
        if not latest_answer:
            return Response(
                {"error": "No questionnaire submission found or submission invalid"},
                status=403,
            )

        # Check if this is the submission we're looking for
        if str(latest_answer.get("id")) != str(answer_id):
            return Response({"error": "Answer ID mismatch"}, status=403)

    except Exception as e:
        logging.error(f"Error querying questionnaire API: {e}")
        return Response(
            {"error": "Failed to verify questionnaire submission"}, status=500
        )

    # Step 2: Extract OTP and quest_id from submission
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

    # Step 3: Validate submission timestamp after OTP extraction
    try:
        submitted_at_str = latest_answer.get("submitted_at")

        submitted_at = dateutil.parser.parse(submitted_at_str).timestamp()

        # Additional validation: check submission is after initiation and within window
        if submitted_at < initiated_at or (submitted_at - initiated_at) > OTP_TIME_OUT:
            return Response(
                {"error": "Submission timestamp outside validity window"}, status=401
            )

    except (ValueError, TypeError) as e:
        logging.error(f"Error parsing submission timestamp: {e}")
        return Response({"error": "Invalid submission timestamp"}, status=401)

    # Step 4: StepVerify temp_token matches
    if expected_temp_token != temp_token:
        return Response({"error": "Invalid temp_token"}, status=401)

    # Step 5: Look up temp_token state record
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

    # Step 6: Update state to verified and add user details
    state_data.update(
        {
            "status": "verified",
            "account": account,
            "verified_at": time.time(),
            "answer_id": answer_id,
        }
    )

    # Update temp_token_state in Redis with refreshed TTL
    r.setex(state_key, TEMP_TOKEN_TIMEOUT, json.dumps(state_data))
    expires_at = int(time.time() + TEMP_TOKEN_TIMEOUT)

    # Clear rate limiting on success
    r.delete(rate_limit_key)

    logging.info(
        f"Successfully verified temp_token for user {account} with action {action}"
    )

    # For login action, handle immediate session creation and cleanup
    is_logged_in = False
    if action == "login":
        try:
            # Create user session immediately for login
            ifsuccess = create_user_session(request, account)
            if ifsuccess:
                is_logged_in = True
                # Delete temp_token_state after successful login
                r.delete(state_key)
                logging.info(
                    f"User {account} logged in successfully, temp_token_state cleaned up"
                )
        except Exception as e:
            logging.error(f"Error creating session for login: {e}")
            return Response({"error": "Failed to create user session"}, status=500)

    # Create response
    response = Response(
        {"action": action, "expires_at": expires_at, "is_logged_in": is_logged_in},
        status=200,
    )

    # Clear temp_token cookie if login succeeded
    if is_logged_in:
        response.delete_cookie("temp_token")

    return response


def create_user_session(request, username) -> bool:
    """
    Helper function to create authenticated session for verified user
    Includes session management and Student model integration similar to auth_login_api
    but returns boolean success
    """
    try:
        # Ensure session exists - create one if it doesn't exist
        if not request.session.session_key:
            request.session.create()

        # Get or create user
        User = get_user_model()

        user, _ = User.objects.get_or_create(
            username=username, defaults={"email": f"{username}@sjtu.edu.cn"}
        )

        # Ensure user is active
        if not user.is_active:
            logging.warning(f"Inactive user attempted OAuth login: {username}")
            return False

        # Create Django session
        login(request, user)

        # Handle Student model integration and session tracking
        # This preserves anonymous session data by linking it to the authenticated user
        if "user_id" in request.session:
            try:
                student = Student.objects.get(user=user)
                # Append the anonymous session ID to track previous unauth activity
                if request.session["user_id"] not in student.unauth_session_ids:
                    student.unauth_session_ids.append(request.session["user_id"])
                    student.save()
            except Student.DoesNotExist:
                # Create new Student record with the anonymous session ID
                student = Student.objects.create(
                    user=user, unauth_session_ids=[request.session["user_id"]]
                )

        # Update session to use authenticated username
        request.session["user_id"] = user.username

        logging.info(f"Successfully created OAuth session for user: {username}")
        return True

    except Exception as e:
        logging.error(f"Error creating user session: {e}")
        return False


def validate_password_strength(password) -> bool:
    """
    Helper function to validate password complexity and strength.
    Custom requirements: More than 12 characters, at least one uppercase, lower case letter and numeric digit.
    Also uses Django's built-in validators for additional security.

    Returns: bool (True if valid, False if invalid)
    """
    # Quick length check first
    if len(password) <= 12:
        return False

    # Single regex pattern to check all character requirements at once
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).*$"
    if not re.match(pattern, password):
        return False

    # Use Django's built-in validators for additional checks
    try:
        validate_password(password)
        return True
    except:
        return False


def handle_signup_user(account, password, request) -> tuple:
    """
    Helper function to handle user creation and session creation for signup action.
    Will return error if user already exists.
    Returns: user or None,error_response or None.
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=account, defaults={"email": f"{account}@sjtu.edu.cn"}
    )
    if not created:
        return None, Response(
            {"error": "User already exists with password. Please use reset password."},
            status=409,
        )

    # Set password
    user.set_password(password)
    user.save()

    # Create user session (log them in)
    if not create_user_session(request, account):
        return None, Response(
            {"error": "user created but failed to log in"}, status=500
        )
    # no error
    return user, None


def handle_reset_password_user(account, password, request) -> tuple:
    """
    Helper function to handle password reset for reset_password action.
    Ensures user is logged in and the account matches their username.
    Returns: user or none, error_response or None
    """
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return None, Response(
            {"error": "User must be logged in to reset password"}, status=401
        )

    # Check if the account in temp_token matches the logged-in user
    if request.user.username != account:
        return None, Response(
            {
                "error": "Account mismatch: temp_token account does not match logged-in user"
            },
            status=403,
        )

    # Get the user object and update password
    User = get_user_model()
    try:
        user = User.objects.get(username=account)
        user.set_password(password)
        user.save()
        # no error
        return user, None

    except:
        return None, Response({"error": "error when reseting password"}, status=500)


@api_view(["POST"])
def auth_password_api(request):
    """
    Set Password API (/api/auth/password)

    Uses verified temp_token to set user password for signup or reset_password actions.
    Should be called after verify_callback_api for signup/reset_password actions.
    """
    try:
        # Get password from request data
        password = request.data.get("password")
        next_url = request.data.get("next", "/courses")
        if not password:
            return Response({"error": "Missing password"}, status=400)

        # Validate password strength first (before any operations)
        is_valid = validate_password_strength(password)
        if not is_valid:
            return Response({"error": "Password validation failed."}, status=400)

        # Get temp_token from HttpOnly cookie
        temp_token = request.COOKIES.get("temp_token")
        if not temp_token:
            return Response({"error": "No temp_token found"}, status=401)

        r = get_redis_connection("default")

        # Look up temp_token state record
        temp_token_hash = hashlib.sha256(temp_token.encode()).hexdigest()
        state_key = f"temp_token_state:{temp_token_hash}"
        state_data = r.get(state_key)

        if not state_data:
            return Response(
                {"error": "Temp token state not found or expired"}, status=401
            )

        try:
            state_data = json.loads(state_data)
        except json.JSONDecodeError:
            return Response({"error": "Invalid temp token state data"}, status=401)

        # Verify status is verified
        if state_data.get("status") != "verified":
            return Response({"error": "Temp token not verified"}, status=401)

        # Verify action is valid for password setting
        action = state_data.get("action")
        if action not in ["signup", "reset_password"]:
            return Response(
                {"error": "Invalid action for password setting"}, status=403
            )

        # Get account from verified state
        account = state_data.get("account")
        if not account:
            return Response({"error": "No account in verified state"}, status=401)

        # Handle user operations based on action using helper functions
        user, error_response = (
            handle_signup_user(account=account, password=password, request=request)
            if action == "signup"
            else handle_reset_password_user(
                account=account, password=password, request=request
            )
        )
        if error_response:
            return error_response

        # Delete temp_token_state after successful password setting and clear cookie
        r.delete(state_key)
        logging.info(
            f"User {account} successfully set password for {action}, temp_token_state cleaned up"
        )
        response = Response(
            {"success": True, "next": next_url, "username": user.username}, status=200
        )
        # Clear the temp_token cookie and return the action-specific response
        response.delete_cookie("temp_token")
        return response

    except Exception as e:
        logging.error(f"Error in auth_password_api: {e}")
        return Response({"error": "Failed to set password"}, status=500)
