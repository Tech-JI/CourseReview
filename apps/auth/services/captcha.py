import logging

import httpx

from django.conf import settings

from apps.auth.services.types import ServiceError

logger = logging.getLogger(__name__)

AUTH_SETTINGS = settings.AUTH
OTP_TIMEOUT = AUTH_SETTINGS["OTP_TIMEOUT"]


async def verify_turnstile_token(
    turnstile_token,
    client_ip,
) -> tuple[bool, ServiceError | None]:
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

        response_data = response.json()
        if not response_data.get("success"):
            logger.warning("Turnstile verification failed: %s", response_data)

            return False, ServiceError(
                "Turnstile verification failed",
                status=403,
            )

        return True, None

    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out")

        return False, ServiceError(
            "Turnstile verification timed out",
            status=504,
        )

    except Exception:
        logger.exception("Turnstile verification error")

        return False, ServiceError(
            "Turnstile verification error",
            status=500,
        )
