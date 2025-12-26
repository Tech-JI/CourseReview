from django.contrib import admin
from django.urls import include, re_path

urlpatterns = [
    # administrative
    re_path(r"^admin/", admin.site.urls),
    # API routes
    re_path(r"^api/auth/", include("apps.auth.urls")),
    re_path(r"^api/", include("apps.web.urls")),
    # Spider routes
    re_path(r"^spider/", include("apps.spider.urls")),
]
