from django.urls import re_path
from apps.auth import views as auth_views

urlpatterns = [
    re_path(r"^init/$", auth_views.auth_initiate_api, name="auth_initiate_api"),
    re_path(r"^verify/$", auth_views.verify_callback_api, name="verify_callback_api"),
    re_path(
        r"^password/$",
        auth_views.auth_reset_password_api,
        name="auth_reset_password_api",
    ),
    re_path(r"^signup/$", auth_views.auth_signup_api, name="auth_signup_api"),
    re_path(r"^login/$", auth_views.auth_login_api, name="auth_login_api"),
    re_path(r"^logout/?$", auth_views.auth_logout_api, name="auth_logout_api"),
]
