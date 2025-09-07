import json
import httpx
import asyncio
import logging
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib.auth.models import User
from django_redis import get_redis_connection
from django.conf import settings
from apps.web.models import Student
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["POST"])
def initiate_login_api(request):
    """
    Step 1: Login Initiation (/api/auth/initiate)

    1. The Vue frontend renders a Cloudflare Turnstile widget.
    2. On successful completion, the frontend sends POST /api/auth/initiate with the Turnstile token.
    3. The Django view verifies the Turnstile token with Cloudflare's API.
    4. On success, it retrieves the user's sessionid and client IP from trusted header.
    5. It creates a Redis key login_intent:<session_id> with JSON value and TTL of 120 seconds.
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
    login_intent_data = {
        "initiated_at": time.time(),  # Unix timestamp
    }

    # Store with 120 seconds TTL as specified
    r.setex(
        f"login_intent:{session_id}",
        120,  # 2 minutes TTL
        json.dumps(login_intent_data),
    )

    logging.info(f"Created login intent for session {session_id} from IP {client_ip}")

    # Return success with questionnaire redirect URL
    return Response(
        {
            "redirect_url": settings.SURVEY_URL,  # The pre-configured questionnaire URL
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

    # Clear old verification state
    r = get_redis_connection("default")
    r.delete(f"session:{session_id}")

    return Response(
        {
            "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
            "SURVEY_URL": settings.SURVEY_URL,
            "session_id": session_id,
        },
        status=200,
    )
