"""layup_list URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.urls import path, include
    3. Add a URL to urlpatterns:  path('blog/', include(blog_urls))
"""

from django.urls import include, re_path
from django.contrib import admin
import django.contrib.auth.views as authviews

from apps.web import views
from apps.analytics import views as aviews
from apps.recommendations import views as rviews
from apps.spider import views as spider_views

urlpatterns = [
    # administrative
    re_path(r"^admin/", admin.site.urls),
    #     re_path(r'^hijack/', include('hijack.urls')),
    # analytics
    # re_path(r"^api/user/$", views.get_user, name="get_user"),
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
    re_path(r"^$", views.landing, name="landing"),
    re_path(r"^(?P<sort>best|layups)/?", views.current_term, name="current_term"),
    re_path(r"^search/?", views.course_search, name="course_search"),
    re_path(
        r"^course/(?P<course_id>[0-9]+)$", views.course_detail, name="course_detail"
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9]+)/$",
        views.course_detail_api,
        name="course_detail_api",
    ),
    re_path(
        r"^course/(?P<course_id>[0-9]+)/review_search/?",
        views.course_review_search,
        name="course_review_search",
    ),
    re_path(r"^departments/?", views.departments, name="departments"),
    # recommendations
    re_path(r"^recommendations/?", rviews.recommendations, name="recommendations"),
    # api
    re_path(
        r"^api/course/(?P<course_id>[0-9].*)/medians", views.medians, name="medians"
    ),
    re_path(
        r"^api/course/(?P<course_id>[0-9].*)/professors?/?",
        views.course_professors,
        name="course_professors",
    ),
    re_path(r"^api/course/(?P<course_id>[0-9].*)/vote", views.vote, name="vote"),
    # authentication
    re_path(r"^accounts/signup$", views.signup, name="signup"),
    re_path(r"^accounts/login/$", views.auth_login, name="auth_login"),
    re_path(r"^accounts/logout$", views.auth_logout, name="auth_logout"),
    re_path(r"^accounts/confirmation$", views.confirmation, name="confirmation"),
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
