import logging

from django.conf import settings
from django.contrib.auth import logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.auth import services, utils

logger = logging.getLogger(__name__)


def _service_error_response(error: services.ServiceError) -> Response:
    return Response(error.as_payload(), status=error.status)


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

    intent, error = services.initiate_auth(request)
    if intent is None:
        return _service_error_response(
            error or services.ServiceError("Failed to initiate authentication", 500),
        )

    # Create response and set temp_token as HttpOnly cookie
    response = Response(
        {"otp": intent.otp, "redirect_url": intent.redirect_url},
        status=200,
    )
    response.set_cookie(
        "temp_token",
        intent.temp_token,
        max_age=services.TEMP_TOKEN_TIMEOUT,
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

    verification, error = services.verify_callback(request)
    if verification is None:
        return _service_error_response(
            error or services.ServiceError("Verification failed", 400),
        )

    # Create response
    response = Response(
        {
            "action": verification.action,
            "expires_at": verification.expires_at,
            "is_logged_in": verification.is_logged_in,
        },
        status=200,
    )

    # Clear temp_token cookie if login succeeded
    if verification.is_logged_in:
        response.delete_cookie("temp_token")

    return response


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
@permission_classes([AllowAny])
def auth_signup_api(request) -> Response:
    """Signup API (/api/auth/signup)

    Handles user signup using verified temp_token.
    """

    data, error = services.complete_signup(request)
    if data is None:
        return _service_error_response(
            error or services.ServiceError("Failed to complete signup", 500),
        )

    response = Response(data, status=200)
    response.delete_cookie("temp_token")

    return response


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
@permission_classes([AllowAny])
def auth_reset_password_api(request) -> Response:
    """Reset Password API (/api/auth/password)

    Handles password reset using verified temp_token.
    """

    data, error = services.reset_password(request)
    if data is None:
        return _service_error_response(
            error or services.ServiceError("Failed to reset password", 500),
        )

    response = Response(data, status=200)
    response.delete_cookie("temp_token")

    return response


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_login_api(request) -> Response:
    data, error = services.login_with_password(request)
    if data is None:
        return _service_error_response(
            error or services.ServiceError("Failed to login", 500),
        )

    return Response(data, status=200)


@api_view(["POST"])
@authentication_classes([utils.CSRFCheckSessionAuthentication])
@permission_classes([AllowAny])
def auth_logout_api(request) -> Response:
    """Logout a user."""

    logger.info(
        "auth_logout_api called for user=%s",
        getattr(request.user, "username", None),
    )
    logout(request)

    return Response({"message": "Logged out successfully"}, status=200)
