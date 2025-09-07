from django.apps import AppConfig


class OAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth"
    label = "oauth"  # Unique label to avoid conflict with django.contrib.auth
