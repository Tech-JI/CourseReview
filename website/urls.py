import django.contrib.auth.views as authviews
from django.contrib import admin
from django.urls import re_path


from apps.auth import views as auth_views
from apps.analytics import views as aviews
from apps.recommendations import views as rviews
from apps.spider import views as spider_views
from apps.web import views

urlpatterns = [
    # OAuth
    re_path(
        r"^api/auth/initiate/$",
        auth_views.auth_initiate_api,
        name="auth_initiate_api",
    ),
    re_path(r"^api/auth/config/$", auth_views.auth_config_api, name="auth_config_api"),
    re_path(
        r"^api/auth/verify/$",
        auth_views.verify_callback_api,
        name="verify_callback_api",
    ),
    re_path(
        r"^api/auth/password/$", auth_views.auth_password_api, name="auth_password_api"
    ),
    # email+password login(the path is not set to auth because it was used in many places)
    re_path(r"^api/accounts/login/$", views.auth_login_api, name="auth_login_api"),
    # log out
    re_path(r"^api/auth/logout/?$", views.auth_logout_api, name="auth_logout_api"),
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
    # password resets(deprecated))
    # re_path(
    #     r"^accounts/password/reset/$",
    #     authviews.PasswordResetView.as_view(
    #         template_name="password_reset_form.html",
    #         html_email_template_name="password_reset_email.html",
    #         email_template_name="password_reset_email.html",
    #     ),
    #     {"post_reset_redirect": "/accounts/password/reset/done/"},
    #     name="password_reset",
    # ),
    # re_path(
    #     r"^accounts/password/reset/done/$",
    #     authviews.PasswordResetDoneView.as_view(
    #         template_name="password_reset_done.html"
    #     ),
    # ),
    # re_path(
    #     r"^accounts/password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
    #     authviews.PasswordResetConfirmView.as_view(
    #         template_name="password_reset_confirm.html"
    #     ),
    #     name="password_reset_confirm",
    # ),
    # re_path(
    #     r"^accounts/password/done/$",
    #     authviews.PasswordResetCompleteView.as_view(
    #         template_name="password_reset_complete.html"
    #     ),
    # ),
]
