import json
import httpx
import asyncio
import logging
import time
import secrets
import base64
import dateutil.parser
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django_redis import get_redis_connection
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.web.models import Student
from rest_framework.decorators import api_view
from rest_framework.response import Response

LOGIN_TIME_OUT = 120  # 2 min


@api_view(["POST"])
def initiate_login_api(request):
    """
    Step 1: Login Initiation (/api/auth/initiate)

    1. The Vue frontend renders a Cloudflare Turnstile widget.
    2. On successful completion, the frontend sends POST /api/auth/initiate with the Turnstile token.
    3. The Django view verifies the Turnstile token with Cloudflare's API.
    4. On success, it retrieves the user's sessionid and client IP from trusted header.
    5. It creates a Redis key login_intent:<session_id> with JSON value("initiated_at" and "verification_code") and TTL of LOGIN_TIME_OUT.
    6. The view responds with 200 OK and the redirect URL for the questionnaire.
    """
    # Get Turnstile token from request data
    turnstile_token = request.data.get("turnstile_token")

    if not turnstile_token:
        return Response({"error": "Missing turnstile_token"}, status=400)

    # Get client IP from trusted headers for enhanced Turnstile security
    client_ip = (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )

    # actually seems no need to use asyncio
    async def verify_turnstile():
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": turnstile_token,
                    "remoteip": client_ip,  # Enhanced security for Turnstile
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

    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    if not session_id:
        return Response({"error": "Unable to create session"}, status=500)

    # Create login intent in Redis
    r = get_redis_connection("default")

    # Generate 8-digit random code using secrets for security
    random_bytes = secrets.token_bytes(
        6
    )  # 6 bytes = 8 base64 characters (without padding)
    verification_code = base64.b64encode(random_bytes).decode("ascii")[
        :8
    ]  # Take first 8 characters

    login_intent_data = {
        "initiated_at": time.time(),  # Unix timestamp
        "verification_code": verification_code,  # 8-digit code for user verification
    }

    # Store with LOGIN_TIME_OUT seconds TTL as specified
    r.setex(
        f"login_intent:{session_id}",
        LOGIN_TIME_OUT,
        json.dumps(login_intent_data),
    )

    logging.info(
        f"Created login intent for session {session_id} with code {verification_code}"
    )

    # Return success with questionnaire redirect URL and verification code
    return Response(
        {
            "redirect_url": settings.SURVEY_URL,  # The pre-configured questionnaire URL
            "verification_code": verification_code,  # 8-digit code for user to enter
        },
        status=200,
    )


@api_view(["GET"])
def auth_config_api(request):
    """
    API endpoint to provide configuration for the frontend
    """
    # Force session creation
    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    if not session_id:
        return Response({"error": "Unable to create session"}, status=500)

    return Response(
        {
            "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
            "SURVEY_URL": settings.SURVEY_URL,
        },
        status=200,
    )


async def get_latest_answer(account: str) -> dict:
    """
    Fetch the latest questionnaire answer for a given account from the WJ API.
    Returns filtered data with only: id(the answer id), ip_address, submitted_at, user.account and verification_code from the row
    """
    WJ_API_KEY = settings.WJ_API_KEY
    if not WJ_API_KEY:
        logging.error("WJ_API_KEY is not configured")
        return {}

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
    full_url_path = f"{BASE_URL}/{WJ_API_KEY}/json"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            full_url_path, params=final_query_params, timeout=LOGIN_TIME_OUT
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
                "ip_address": latest_answer.get("ip_address"),
                "submitted_at": latest_answer.get("submitted_at"),
                "account": latest_answer.get("user", {}).get("account")
                if latest_answer.get("user")
                else None,
                "verification_code": verification_code,
            }

            return filtered_data

        return {}


@api_view(["POST"])
def verify_callback_api(request):
    """
    Step 4: Callback Verification (/api/auth/verify)

    Handles the verification of questionnaire callback with race condition protection
    and IP-based priority system
    """

    # Get username and answer_id from request
    username = request.data.get("username")
    answer_id = request.data.get("answer_id")

    if not username or not answer_id:
        return Response({"error": "Missing username or answer_id"}, status=400)

    # Ensure session exists
    if not request.session.session_key:
        return Response({"error": "No session found"}, status=401)

    session_id = request.session.session_key
    r = get_redis_connection("default")

    # Step 1: Consume login intent
    login_intent_key = f"login_intent:{session_id}"
    intent_data = r.get(login_intent_key)

    if not intent_data:
        return Response({"error": "Login intent expired or not found"}, status=401)

    # Delete the intent immediately to prevent reuse
    r.delete(login_intent_key)

    try:
        intent_data = json.loads(intent_data)
        initiated_at = intent_data.get("initiated_at")
        expected_verification_code = intent_data.get("verification_code")
    except (json.JSONDecodeError, AttributeError):
        return Response({"error": "Invalid login intent data"}, status=401)

    # Step 2: Query questionnaire API
    try:
        latest_answer = asyncio.run(get_latest_answer(username))
        if not latest_answer:
            return Response({"error": "No questionnaire submission found"}, status=403)

        # Check if this is the submission we're looking for
        if str(latest_answer.get("id")) != str(answer_id):
            return Response({"error": "Answer ID mismatch"}, status=403)

    except Exception as e:
        logging.error(f"Error querying questionnaire API: {e}")
        return Response(
            {"error": "Failed to verify questionnaire submission"}, status=500
        )

    # Step 3: Validate submission timestamp
    try:
        submitted_at_str = latest_answer.get("submitted_at")
        submitted_at = dateutil.parser.parse(submitted_at_str).timestamp()

        # Check if submission is within 2-minute window
        time_diff = submitted_at - initiated_at
        if time_diff <= 0 or time_diff >= LOGIN_TIME_OUT:
            return Response(
                {"error": "Submission timestamp outside valid window"}, status=401
            )

    except (ValueError, TypeError) as e:
        logging.error(f"Error parsing submission timestamp: {e}")
        return Response({"error": "Invalid submission timestamp"}, status=401)

    # Step 4: Verify the 8-digit code matches
    submitted_code = latest_answer.get("verification_code")
    if not submitted_code or submitted_code != expected_verification_code:
        logging.warning(
            f"Verification code mismatch for user {username}. Expected: {expected_verification_code}, Got: {submitted_code}"
        )
        return Response({"error": "Invalid verification code"}, status=403)

    logging.info(f"Verification code validated successfully for user {username}")

    # # Not needed
    # # Step 5: Simple IP verification
    # submission_ip = latest_answer.get("ip_address")
    # request_ip = (
    #     request.META.get("HTTP_CF_CONNECTING_IP")
    #     or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    #     or request.META.get("REMOTE_ADDR")
    # )

    # # Log IP information for debugging
    # if submission_ip == request_ip:
    #     logging.info(f"IP match verification for answer_id: {answer_id}, IP: {request_ip}")
    # else:
    #     logging.info(f"IP mismatch for answer_id: {answer_id}, submission_ip: {submission_ip}, request_ip: {request_ip}")

    # Proceed to create session regardless of IP match
    return create_user_session(request, username)


def create_user_session(request, username):
    """
    Helper function to create authenticated session for verified user
    Includes session management and Student model integration similar to auth_login_api
    """
    try:
        # Get or create user
        User = get_user_model()

        user, _ = User.objects.get_or_create(
            username=username, defaults={"email": f"{username}@sjtu.edu.cn"}
        )

        # Ensure user is active
        if not user.is_active:
            logging.warning(f"Inactive user attempted OAuth login: {username}")
            return Response(
                {"error": "The user is inactive."},
                status=403,
            )

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

        return Response(
            {
                "message": "Authentication successful",
                "username": username,
                "redirect_url": "/courses",  # Match the next_url from traditional login
            },
            status=200,
        )

    except Exception as e:
        logging.error(f"Error creating user session: {e}")
        return Response({"error": "Failed to create session"}, status=500)
