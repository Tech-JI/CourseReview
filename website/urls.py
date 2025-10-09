from django.contrib import admin
from django.urls import include, re_path

from apps.auth import views as auth_views
from apps.spider import views as spider_views
from apps.web import views

urlpatterns = [
    re_path(
        r"^api/auth/init/$",
        auth_views.auth_initiate_api,
        name="auth_initiate_api",
    ),
    re_path(
        r"^api/auth/verify/$",
        auth_views.verify_callback_api,
        name="verify_callback_api",
    ),
    re_path(
        r"^api/auth/password/$",
        auth_views.auth_reset_password_api,
        name="auth_reset_password_api",
    ),
    re_path(r"^api/auth/signup/$", auth_views.auth_signup_api, name="auth_signup_api"),
    # email+password login
    re_path(r"^api/auth/login/$", auth_views.auth_login_api, name="auth_login_api"),
    # log out
    re_path(r"^api/auth/logout/?$", auth_views.auth_logout_api, name="auth_logout_api"),
    # administrative
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^api/user/status/?", views.user_status, name="user_status"),
    # spider
    re_path(r"^spider/data/$", spider_views.crawled_data_list, name="crawled_datas"),
    re_path(
        r"^spider/data/(?P<crawled_data_pk>[0-9]+)$",
        spider_views.crawled_data_detail,
        name="crawled_data",
    ),
    # primary views
    re_path(r"^api/landing/$", views.landing_api, name="landing_api"),
    re_path(
        r"^api/courses/(?P<course_id>[0-9]+)/$",
        views.CoursesDetailAPI.as_view(),
        name="course_detail_api",
    ),
    re_path(
        r"^api/courses/(?P<course_id>[0-9].*)/instructors?/?",
        views.course_instructors,
        name="course_instructors",
    ),
    re_path(
        r"^api/courses/(?P<course_id>[0-9].*)/medians", views.medians, name="medians"
    ),
    re_path(
        r"^api/courses/(?P<course_id>[0-9].*)/professors?/?",
        views.course_professors,
        name="course_professors",
    ),
    re_path(
        r"^api/courses/(?P<course_id>[0-9].*)/vote",
        views.course_vote_api,
        name="course_vote_api",
    ),
    re_path(
        r"^api/courses/(?P<course_id>[0-9]+)/reviews/$",
        views.CoursesReviewsAPI.as_view(),
        name="course_review_api",
    ),
    re_path(
        r"^api/reviews/?$",
        views.UserReviewsAPI.as_view(),
        name="user_reviews_api",
    ),
    re_path(
        r"^api/reviews/(?P<review_id>[0-9]+)/$",
        views.UserReviewsAPI.as_view(),
        name="user_review_api",
    ),
    re_path(
        r"^api/reviews/(?P<review_id>[0-9]+)/vote/$",
        views.review_vote_api,
        name="review_vote_api",
    ),
    re_path(
        r"^api/departments/$",
        views.departments_api,
        name="departments_api",
    ),
    re_path(r"^api/courses/$", views.CoursesListAPI.as_view(), name="courses_api"),
]
