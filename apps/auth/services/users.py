import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser

from apps.auth.services.types import ServiceError
from apps.web.models import Student

logger = logging.getLogger(__name__)

AUTH_SETTINGS = settings.AUTH
EMAIL_DOMAIN_NAME = AUTH_SETTINGS["EMAIL_DOMAIN_NAME"]


def create_user_session(
    request,
    account,
) -> tuple[AbstractUser | None, ServiceError | None]:
    """Helper function includes session management, user creation and Student model integration."""

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
            return None, ServiceError(
                "Failed to retrieve or create user",
                status=500,
            )

        # Handle Student model integration
        Student.objects.get_or_create(user=user)

        # Update session to use authenticated username
        request.session["user_id"] = user.username

        return user, None

    except Exception:
        logger.exception("Failed to create user session")

        return None, ServiceError(
            "Failed to create user session",
            status=500,
        )
