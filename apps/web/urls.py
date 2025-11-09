from django.urls import re_path
from apps.web import views

urlpatterns = [
    re_path(r"^user/status/?", views.user_status, name="user_status"),
    re_path(r"^landing/$", views.landing_api, name="landing_api"),
    re_path(r"^courses/$", views.CoursesListAPI.as_view(), name="courses_api"),
    re_path(
        r"^courses/(?P<course_id>[0-9]+)/$",
        views.CoursesDetailAPI.as_view(),
        name="course_detail_api",
    ),
    re_path(
        r"^courses/(?P<course_id>[0-9].*)/instructors?/?",
        views.course_instructors,
        name="course_instructors",
    ),
    re_path(r"^courses/(?P<course_id>[0-9].*)/medians", views.medians, name="medians"),
    re_path(
        r"^courses/(?P<course_id>[0-9].*)/professors?/?",
        views.course_professors,
        name="course_professors",
    ),
    re_path(
        r"^courses/(?P<course_id>[0-9].*)/vote",
        views.course_vote_api,
        name="course_vote_api",
    ),
    re_path(
        r"^courses/(?P<course_id>[0-9]+)/reviews/$",
        views.CoursesReviewsAPI.as_view(),
        name="course_review_api",
    ),
    re_path(r"^reviews/?$", views.UserReviewsAPI.as_view(), name="user_reviews_api"),
    re_path(
        r"^reviews/(?P<review_id>[0-9]+)/$",
        views.UserReviewsAPI.as_view(),
        name="user_review_api",
    ),
    re_path(
        r"^reviews/(?P<review_id>[0-9]+)/vote/$",
        views.review_vote_api,
        name="review_vote_api",
    ),
    re_path(r"^departments/$", views.departments_api, name="departments_api"),
]
