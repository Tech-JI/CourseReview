import django.contrib.auth.views as authviews
from django.contrib import admin
from django.urls import re_path

from django.urls import include
from apps.verifier.views import webhook
from apps.verifier import views as verifier_views
from django.shortcuts import redirect
from django.conf import settings

from apps.analytics import views as aviews
from apps.recommendations import views as rviews
from apps.spider import views as spider_views
from apps.web import views

urlpatterns = [
    # Verification endpoints - RESTful API under /api/accounts/verify
    re_path(r"^api/accounts/verify/$", verifier_views.verify_page, name="verify_page"),
    re_path(
        r"^api/accounts/verify/turnstile/$",
        verifier_views.verify_turnstile,
        name="verify_turnstile",
    ),
    re_path(
        r"^api/accounts/verify/sse/$", verifier_views.sse_status, name="sse_status"
    ),
    re_path(
        r"^api/accounts/verify/complete/$",
        verifier_views.complete_login,
        name="complete_login",
    ),
    re_path(
        r"^api/accounts/verify/config/$",
        verifier_views.verify_config,
        name="verify_config",
    ),
    # Webhook endpoint (separate from API structure)
    re_path(r"^webhook/?", webhook, name="webhook"),
    # old email+password login (only for admin use, not for students)
    re_path(r"^api/accounts/login/$", views.auth_login_api, name="auth_login_api"),
    # administrative
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^api/user/status/?", views.user_status, name="user_status"),
    re_path(r"^analytics/$", aviews.home, name="analytics_home"),
    re_path(
        r"^eligible_for_recommendations/$",
        aviews.eligible_for_recommendations,
        name="eligible_for_recommendations",
    ),
    re_path(
        r"^sentiment_labeler/$", aviews.sentiment_labeler, name="sentiment_labeler"
    ),
    # spider
    re_path(r"^spider/data/$", spider_views.crawled_data_list, name="crawled_datas"),
    re_path(
        r"^spider/data/(?P<crawled_data_pk>[0-9]+)$",
        spider_views.crawled_data_detail,
        name="crawled_data",
    ),
    # primary views
    # homepage redirecting to this path will be handling by the frontend
    re_path(r"^api/landing/$", views.landing_api, name="landing_api"),
    re_path(
        r"^api/course/(?P<course_id>[0-9]+)/$",
        views.course_detail_api,
        name="course_detail_api",
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9].*)/instructors?/?",
        views.course_instructors,
        name="course_instructors",
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9].*)/medians", views.medians, name="medians"
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9].*)/professors?/?",
        views.course_professors,
        name="course_professors",
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9].*)/vote",
        views.course_vote_api,
        name="course_vote_api",
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9]+)/review/$",
        views.delete_review_api,
        name="delete_review_api",
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9]+)/my-review/$",
        views.get_user_review_api,
        name="get_user_review_api",
    ),
    re_path(
        r"^api/review/(?P<review_id>[0-9]+)/vote/$",
        views.review_vote_api,
        name="review_vote_api",
    ),
    re_path(
        r"^api/departments/$",
        views.departments_api,
        name="departments_api",
    ),
    re_path(r"^api/courses/$", views.courses_api, name="courses_api"),
    re_path(
        r"^api/course/(?P<course_id>[0-9]+)/review_search/$",
        views.course_review_search_api,
        name="course_review_search_api",
    ),
    # recommendations
    re_path(r"^recommendations/?", rviews.recommendations, name="recommendations"),
    re_path(r"^api/auth/logout/?$", views.auth_logout_api, name="auth_logout_api"),
    # password resets
    re_path(
        r"^accounts/password/reset/$",
        authviews.PasswordResetView.as_view(
            template_name="password_reset_form.html",
            html_email_template_name="password_reset_email.html",
            email_template_name="password_reset_email.html",
        ),
        {"post_reset_redirect": "/accounts/password/reset/done/"},
        name="password_reset",
    ),
    re_path(
        r"^accounts/password/reset/done/$",
        authviews.PasswordResetDoneView.as_view(
            template_name="password_reset_done.html"
        ),
    ),
    re_path(
        r"^accounts/password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
        authviews.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    re_path(
        r"^accounts/password/done/$",
        authviews.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html"
        ),
    ),
]
